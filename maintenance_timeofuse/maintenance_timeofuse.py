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
import time

from openerp import models, fields, api, _

class maintenance_element(models.Model):
    _inherit = 'maintenance.element'

    @api.one
    def _get_last_timeofuse(self):

        last_timeofuse = self.env['maintenance.intervention.timeofuse'].search([('maintenance_element_id','=',self.id)],order='date desc, time_of_use desc', limit=1)
        
        if last_timeofuse:
            self.time_of_use = last_timeofuse.time_of_use
        else:
            self.time_of_use = 0.

    time_of_use = fields.Float(compute='_get_last_timeofuse', string='Last time of use')
    timeofuse_required = fields.Boolean('Hour counter required')
    timeofuse_history = fields.One2many('maintenance.intervention.timeofuse', 'maintenance_element_id', string="Time of use history" )

class maintenance_intervention_timeofuse(models.Model):
    _name = 'maintenance.intervention.timeofuse'
    
    _rec_name = 'maintenance_element_id'
    
    #a timeofuse record is valid (usable) if intervention is done
    @api.depends('intervention_id','intervention_id.state')
    @api.one
    def _get_valid(self):
        if not self.intervention_id:
            self.valid = True
        elif self.intervention_id.state == 'done':
            self.valid = True
        else:
            self.valid = False

    date = fields.Datetime("Date",default=lambda *a: time.strftime('%Y-%m-%d'))
    intervention_id = fields.Many2one('maintenance.intervention', string="Intervention")
    maintenance_element_id = fields.Many2one('maintenance.element', string="Maintenance element")
    time_of_use = fields.Float("Time of use (h)")
    valid = fields.Boolean(compute=_get_valid,  string="Valid", store=True)

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
                    
        
        return super(maintenance_intervention, self).action_done()

