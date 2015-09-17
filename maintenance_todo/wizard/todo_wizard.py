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


class add_todo(models.TransientModel):
    _name='maintenance.todo.add'
    
    @api.multi
    def _get_installation(self):
       
        if self.env.context.has_key('active_id') and self.env.context.has_key('active_model') and self.env.context['active_model']== 'maintenance.intervention':
            intervention = self.env['maintenance.intervention'].browse(self.env.context['active_id'])
            if intervention.installation_id:
                return intervention.installation_id.id
        else:
            return self.env['maintenance.installation']
        '''
        if self.intervention_id:
            return self.intervention_id.installation_id.id
         '''
    
    @api.multi
    def _get_intervention(self):
        if self.env.context.has_key('active_id') and self.env.context.has_key('active_model') and self.env.context['active_model']== 'maintenance.intervention':
            return self.env.context['active_id']
        else:
            return self.env['maintenance.intervention']
    
    description = fields.Text('Description',required=True)
    
    installation_id = fields.Many2one('maintenance.installation',string="Installation", default=_get_installation,readonly=True)
    intervention_id = fields.Many2one('maintenance.intervention',string="Intervention", default=_get_intervention,readonly=True)
    
    
    @api.one
    def confirm_todo(self):
        if self.installation_id:
            value = {'installation_id' : self.installation_id.id,
                     'description' : self.description,
                     'intervention_from_id':self.intervention_id.id,
                     'ask_user_id' : self.env.user.id
                     }
            todo = self.env['maintenance.todo'].create(value)
            
            
class assign_to(models.TransientModel):
    _name='maintenance.todo.assign.to'
    
    @api.multi
    def _get_installation(self):
       
        if self.env.context.has_key('active_id') and self.env.context.has_key('active_model') and self.env.context['active_model']== 'maintenance.todo':
            todo = self.env['maintenance.todo'].browse(self.env.context['active_id'])
            if todo.installation_id:
                return todo.installation_id.id
        else:
            return self.env['maintenance.installation']
        
    @api.multi
    def _get_intervention_from(self):
       
        if self.env.context.has_key('active_id') and self.env.context.has_key('active_model') and self.env.context['active_model']== 'maintenance.todo':
            todo = self.env['maintenance.todo'].browse(self.env.context['active_id'])
            if todo.intervention_from_id:
                return todo.intervention_from_id.id
        else:
            return self.env['maintenance.intervention']
    
    intervention_from_id = fields.Many2one('maintenance.intervention',string="Intervention From", default=_get_intervention_from,readonly=True)
    installation_id = fields.Many2one('maintenance.installation',string="Installation", default=_get_installation,readonly=True)
    intervention_id = fields.Many2one('maintenance.intervention',string='Intervention',required=True)
    
    
    @api.one
    def assign_to(self):
        if self.intervention_id and self.env.context.has_key('active_id') and self.env.context.has_key('active_model') and self.env.context['active_model']== 'maintenance.todo':
            todo = self.env['maintenance.todo'].browse(self.env.context['active_id'])
            todo.intervention_assign_id = self.intervention_id
            todo.action_assign()
            
class intervention_confirm_todo(models.TransientModel):
    _name='maintenance.intervention.todo.conf'
    
    
    