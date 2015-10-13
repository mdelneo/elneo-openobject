# -*- coding: utf-8 -*-
##############################################################################
#
#    Elneo
#    Copyright (C) 2011-2015 Elneo (Technofluid SA) (<http://www.elneo.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from datetime import datetime

from openerp import fields, models, api, _
from openerp.exceptions import Warning



class intervention_merge_lines(models.TransientModel):
    _name='maintenance.intervention.merge.lines'
    
    wizard_id = fields.Many2one('maintenance.intervention.merge.wizard',string='Interventions')
    intervention_id = fields.Many2one('maintenance.intervention','Interventions')
    maint_type = fields.Many2one('maintenance.intervention.type','Type')
    date_start = fields.Datetime(string='Planned Start Date')

class intervention_merge(models.TransientModel):
    _name='maintenance.intervention.merge.wizard'
    
    def _get_interventions(self):
        res=[]
        
        if not self.env.context or not self.env.context.has_key('active_ids'):
            return res
        
        ids = self.env.context['active_ids']
        
        
        last_installation_id=None
        interventions = self.env['maintenance.intervention'].browse(ids)
        for intervention in self.env['maintenance.intervention'].browse(ids):
            
            # Check if interventions are linked to the same installation - raise at the first difference
            if(last_installation_id and (last_installation_id <> intervention.installation_id)):
                raise Warning(_('You cannot merge interventions on different installations! Please select interventions on the same installation.'))
            
            if(not intervention.state in ['draft']):
                raise Warning(_('You cannot merge interventions which are not draft!'))

            last_installation_id = intervention.installation_id
            
        return interventions.mapped('id')
    
    # Set the start date as the first selected intervention date 
    def _get_intervention_date(self):
        
        intervention_id = self.env.context.get('active_id',False)
        if intervention_id:
            intervention = self.env['maintenance.intervention'].browse(intervention_id)
            if(intervention.date_start):
                return intervention.date_start
    
    # Set the reference intervention as the first selected one
    def _get_reference_intervention(self):
        intervention_id = self.env.context.get('active_id',False)
        if intervention_id:
            return intervention_id
    
    # Set the reference intervention as the first selected one
    def _get_reference_installation(self):
        intervention_id = self.env.context.get('active_id',False)
        if intervention_id:
            return self.env['maintenance.intervention'].browse(intervention_id).installation_id.id
  
    @api.onchange('reference_intervention')
    def onchange_reference_intervention(self):
        self.reference_installation = self.reference_intervention.installation_id.id
        
    @api.onchange('intervention_lines')
    def onchange_intervention_lines(self):
        # If a reference intervention is set and lines have changed, check if reference intervention is present in the list
        if (self.reference_intervention):
            if (not self.intervention_lines):
                self.reference_intervention = self.env['maintenance.intervention']
           
            if self.reference_intervention not in self.intervention_lines:
                self.reference_intervention = self.env['maintenance.intervention']

    
    intervention_lines = fields.Many2many('maintenance.intervention','maintenance_intervention_merge_rel','wizard_id','intervention_id',default=_get_interventions,string='Interventions')
    date = fields.Datetime(string='Merge Date',default=_get_intervention_date,help='The date where to group the selected interventions')
    reference_intervention = fields.Many2one('maintenance.intervention',default=_get_reference_intervention,string='Reference Intervention',required=True) 
    reference_installation = fields.Many2one('maintenance.installation',default=_get_reference_installation,string='Reference Installation')    
   
    @api.multi
    def getAll(self):
        res={}
        
        data=[]
        
        #Prevent from click twice on Button
        active_model = self.env.context.get('active_model')
        if active_model and active_model =='maintenance.intervention.merge.wizard':
            intervention_ids = self.intervention_lines.mapped('id')
        elif active_model and active_model == 'maintenance.intervention':
            intervention_ids=self.env.context.get('active_ids')
        else:
            intervention_ids = None
        
        if intervention_ids:
            interventions = self.env['maintenance.intervention'].browse(intervention_ids)
            
            self.intervention_lines=None
            for intervention in interventions:
                if (intervention.installation_id.id):
                    interventions_to_append = self.env['maintenance.intervention'].search([('installation_id','=',intervention.installation_id.id),('state','in',['draft'])])
                    #self.intervention_lines += interventions_to_append
                    self.write({'intervention_lines':[(6,0,interventions_to_append.mapped('id'))]})
                    
                    #for intervention_to_append in interventions_to_append:
                    #self.write(cr,uid,ids,{'intervention_lines':[(6,0,interventions_to_append_ids)]},context=context)
                        #data.append(intervention_to_append.id)
        
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.intervention.merge.wizard',
            'name':'Merge interventions',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
             }   
        #self.write(cr,uid,ids,{'intervention_lines':[(4,data)]})
        #self.pool.get('maintenance.intervention.merge.lines').create(cr, uid, {'wizard_id':ids[0],'intervention_id':8220}, context=context)
        
        #return {'nodestroy':True}
    
    # Merging process
    @api.one
    def merge(self):
        res={}
        

        if(not self.reference_intervention):
            raise Warning(_('You didn''t provide any Reference Intervention to help the merging process!'))
        
        # Cancel current interventions
        if (not self._cancel_interventions(self.intervention_lines)):
            raise Warning(_('Merging process interrupted : impossible to change the interventions state.'))
        
        default_attributes = {'date_scheduled':self.date}.copy()
        default_attributes.update(self._get_comments(self.intervention_lines))
        default_attributes.update(self._get_time_planned(self.intervention_lines))
        
        # Duplicate reference intervention
        new_intervention_id = self.reference_intervention.copy(default=default_attributes)
        
        # Get lines that are not reference line
        lines_to_append = self._get_not_ref_lines(self.intervention_lines,self.reference_intervention.id)
        
        # Set the sale_order (the copy in maintenance_product set it to None) - TO CHECK - WHAT IF EACH MERGED INTERVENTION HAS A DIFFERENT SALE ORDER - MANY2MANY????
        #if(wizard.reference_intervention.sale_order_id):
        #    self.pool.get('maintenance.intervention').write(cr,uid,new_intervention_id,{'sale_order_id':wizard.reference_intervention.sale_order_id.id})
        
        # Set all the intervention attributes
        self._set_attributes(lines_to_append, new_intervention_id)
        
        #Create generation details
        self._create_generation_details(new_intervention_id, [intervention.id for intervention in self.intervention_lines])

    
    #create new lines of generation details to link new intervention to intervention models and maintenance elements
    def _create_generation_details(self,new_intervention_id, intervention_ids):
        intervention_detail_lines = self.env['maintenance.generation.detail'].search([('intervention_id','in',intervention_ids)])
        intervention_detail_lines_set = set()
        for intervention_detail_line in intervention_detail_lines:
            intervention_detail_lines_set.add((new_intervention_id.id,intervention_detail_line.intervention_model_id.id,intervention_detail_line.maintenance_element_id.id))
        for intervention_detail_line in intervention_detail_lines_set:
            self.env['maintenance.generation.detail'].create( {
                'intervention_id':intervention_detail_line[0],
                'intervention_model_id':intervention_detail_line[1],
                'maintenance_element_id':intervention_detail_line[2],
            })

    def _cancel_interventions(self,int_list):
        for intervention in int_list:
            intervention.state='cancel'
        
        return True
            
    def _get_comments(self,lines):
        res = {'ext_comment':'','int_comment':'','name':''}
        
        for line in lines:
            if(line.ext_comment):
                res['ext_comment'] = res['ext_comment'] + '\n' + line.ext_comment
            if(line.int_comment):
                res['int_comment'] = res['int_comment'] + '\n' +  line.int_comment
            if(line.name):
                res['name'] = res['name'] + '\n' +  line.name
            
        
        return res
    
    def _get_time_planned(self, lines):
        time_planned = 0
        for line in lines:
            time_planned = time_planned + line.time_planned
        return {'time_planned':time_planned}
        
    def _get_not_ref_lines(self,lines,ref_int):
        res = []
        
        for line in lines:
            if(ref_int and line.id and (line.id != ref_int)):
                res.append(line)
        
        return res
    
    def _set_attributes(self,lines,new_int):
        res = False
        
        maint_element_time_appended=[]
        ref_intervention = new_int
        
        # Select the copied timeofuse elements
        for ref_element in ref_intervention.intervention_timeofuse:
            maint_element_time_appended.append(ref_element.maintenance_element_id.id)
        try:
            
            for line in lines:
                for product in line.intervention_products:
                    # Link the products to the new intervention
                    product.intervention_id = new_int
                    # Link the time of use
                for timeofuse in line.intervention_timeofuse:
                    # Don't copy existing time of use line for a particular maintenance element
                    if not(timeofuse.maintenance_element_id.id in maint_element_time_appended):
                        timeofuse.copy(default={'intervention_id':new_int.id})
                        maint_element_time_appended.append(timeofuse.maintenance_element_id.id)
            res = True
        except Exception,e:
            raise Warning(_('Error during merging. Impossible to copy the interventions attributes to the new one!'))
        
        return res
    
    @api.one
    def make_reference(self,cr,uid,ids,context=None):
        res={'nodestroy':1}
        
        intervention_id = self.env.context.get('active_id',False)
        if(not intervention_id):
            raise Warning(_('Please select an intervention!'))
        
        self.reference_intervention= intervention_id

        return res
