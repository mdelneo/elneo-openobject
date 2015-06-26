'''
Created on 11 juil. 2012

@author: cth
'''

import time



from openerp import models, fields, api, _

class maintenance_intervention_timeofuse(models.Model):
    _name = 'maintenance.intervention.timeofuse'
    
    _rec_name = 'maintenance_element_id'
    
    #a timeofuse record is valid (usable) if intervention is done
    @api.one
    def is_valid(self):
        if not self.intervention_id:
            return True
        elif self.intervention_id.state == 'done':
            return True
        return False
    
    @api.one
    @api.depends('intervention_id','intervention_id.state')
    def _get_valid(self):
        return self.is_valid()
    
    date = fields.Datetime("Date",default=lambda *a: time.strftime('%Y-%m-%d'))
    intervention_id = fields.Many2one('maintenance.intervention', string="Intervention")
    maintenance_element_id = fields.Many2one('maintenance.element', string="Maintenance element")
    time_of_use = fields.Float("Time of use (h)")
    valid = fields.Boolean(compute=_get_valid,  string="Valid", store=True)


class maintenance_element(models.Model):
    _inherit = 'maintenance.element'
    
    @api.one
    @api.depends('timeofuse_history.maintenance_element_id','timeofuse_history.time_of_use')
    def get_last_timeofuse(self):

        last_timeofuse = self.env['maintenance.intervention.timeofuse'].search([('maintenance_element_id','=',self.id)],order='date desc, time_of_use desc', limit=1)
        
        if last_timeofuse:
            self.time_of_use = last_timeofuse.time_of_use
        else:
            self.time_of_use = 0
        
        return True
        
    
    time_of_use = fields.Float(compute = get_last_timeofuse, string='Last time of use',store=True)
    timeofuse_required = fields.Boolean('Hour counter required')
    timeofuse_history = fields.One2many('maintenance.intervention.timeofuse', 'maintenance_element_id', string="Time of use history", domain=['|',('intervention_id.state','=','done'),('intervention_id','=',False)])
       

class maintenance_intervention(models.Model):
    _inherit = 'maintenance.intervention'
 
    intervention_timeofuse=fields.One2many('maintenance.intervention.timeofuse', 'intervention_id', string="Hour counters")
    
    @api.multi
    def action_create_update_sale_order(self):
        res = super(maintenance_intervention, self).action_create_update_sale_order()
        
        self.env['maintenance.intervention.timeofuse'].search([('intervention_id','in',self._ids)]).unlink()
        
        for intervention in self:
            for element in intervention.installation_id.elements.filtered('timeofuse_required'):
                self.env['maintenance.intervention.timeofuse'].create({'intervention_id':intervention.id, 'maintenance_element_id':element.id})
        
        return res
    
    @api.multi
    def action_done(self):
        force = self.env.context.get("intervention_force_done", False)
            
        for intervention in self:
            for timeofuse in intervention.intervention_timeofuse:
                if not force and not timeofuse.time_of_use and timeofuse.maintenance_element_id:
                    #Open popup
                    wizard_id = self.env['maintenance.timeofuse.intervention.confirm.wizard'].with_context(active_ids=self._ids,active_id=intervention.id).create({})
                    
                    model_data = self.env['ir.model.data'].search([('model','=','ir.ui.view'),('name','=','view_maintenance_timeofuse_intervention_confirm_wizard')])
                    resource = model_data.res_id
                    
                    context = self._context.copy()
                    context.update({'active_ids':self._ids,'active_id':intervention.id})
                    
                    return {
                        'name':_("Confirm"),
                        'view_mode': 'form',
                        'view_type': 'form',
                        'view_id': False,
                        'res_model': 'maintenance.timeofuse.intervention.confirm.wizard',
                        #'res_id':wizard_id,
                        'context': context,
                        'views': [(resource,'form')],
                        'type': 'ir.actions.act_window',
                        'nodestroy': True,
                        'target': 'new',
                        
                        
                    }
                    
        
        result = super(maintenance_intervention, self).action_done()
