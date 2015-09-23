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
    
    
    @api.multi
    def assign_to(self):
        self.ensure_one()
        if self.intervention_id and self.env.context.has_key('active_id') and self.env.context.has_key('active_model') and self.env.context['active_model']== 'maintenance.todo':
            todo = self.env['maintenance.todo'].browse(self.env.context['active_id'])
            todo.intervention_assign_id = self.intervention_id
            todo.action_assign()
        
        return True
            
class intervention_confirm_todo(models.TransientModel):
    _name='maintenance.intervention.todo.conf'
    
    @api.multi
    def _get_intervention(self):
       
        if self.env.context.has_key('active_id') and self.env.context.has_key('active_model') and self.env.context['active_model']== 'maintenance.intervention':
            intervention = self.env['maintenance.intervention'].browse(self.env.context['active_id'])
            if intervention:
                return intervention.id
        else:
            return self.env['maintenance.intervention']
    
    intervention_id = fields.Many2one('maintenance.intervention','Intervention',required=True,default=_get_intervention)
    
    @api.one
    def confirm(self):
        if self.intervention_id:
            self.intervention_id.with_context(confirm_todo_anyway=True).action_confirm()
            
    
class intervention_done_todo(models.TransientModel):
    _name='maintenance.intervention.todo.done'
    
    @api.model
    def _get_lines(self):
        res = []
        if self.env.context.get('active_id',False) and self.env.context.get('active_model',False) and self.env.context['active_model'] == 'maintenance.intervention':
            intervention = self.env['maintenance.intervention'].browse(self.env.context.get('active_id',False))
            assigned_todos = intervention.installation_id.todo_ids.filtered(lambda r:r.state in ('assigned'))
            int_todos = assigned_todos.filtered(lambda r:r.intervention_assign_id==intervention)
            for int_todo in int_todos:
                '''
                self.env['maintenance.intervention.todo.done.line'].create({'wizard_id':self.id,
                                                                            'to_be_done':True,
                                                                            'todo_id':int_todo.id
                                                                            })
                '''
                res.append({'to_be_done':True,
                            'todo_id':int_todo.id,
                            'summary':int_todo.summary
                            })
            for todo in (assigned_todos - int_todos):
                '''
                self.env['maintenance.intervention.todo.done.line'].create({'wizard_id':self.id,
                                                                            'to_be_done':False,
                                                                            'todo_id':todo.id
                                                                            })
                '''
                res.append({'to_be_done':False,
                            'todo_id':todo.id,
                            'summary':todo.summary})
        
        return res
    
    @api.multi
    def _get_intervention(self):
       
        if self.env.context.has_key('active_id') and self.env.context.has_key('active_model') and self.env.context['active_model']== 'maintenance.intervention':
            intervention = self.env['maintenance.intervention'].browse(self.env.context['active_id'])
            if intervention:
                return intervention.id
        else:
            return self.env['maintenance.intervention']
    
    intervention_id=fields.Many2one('maintenance.intervention','Intervention',readonly=True,default=_get_intervention)
    line_ids=fields.One2many('maintenance.intervention.todo.done.line','wizard_id','Todo\'s',default=_get_lines)
    
    @api.multi
    def done(self):
        self.ensure_one()
        to_be_done = self.line_ids.filtered('to_be_done')
        # We want to warn manager that an assigned todo was not done by user
        to_be_warn = self.intervention_id.todo_assigned_ids - to_be_done.mapped('todo_id')
        for line in to_be_done:
            if self.intervention_id:
                line.todo_id.intervention_assign_id = self.intervention_id
            line.todo_id.action_done()
        
        if to_be_warn:
            template_id = self.env['ir.model.data'].get_object('maintenance_todo', 'email_template_todo_warn')
            body = self.env['email.template'].render_template(template_id.body_html,'maintenance.intervention',self.intervention_id.id)
            self.intervention_id.message_post(type='email',subtype='subtype_todo_warn',body=body)
        
        self.intervention_id.with_context(todo_done=True).action_done()

class intervention_done_todo_line(models.TransientModel):
    _name = 'maintenance.intervention.todo.done.line'
    
    _rec_name = 'todo_id'

    wizard_id=fields.Many2one('maintenance.intervention.todo.done',string='Todo',readonly=True)
    todo_id=fields.Many2one('maintenance.todo',string='Todo',readonly=True)
    to_be_done=fields.Boolean('To be done')
    summary = fields.Char('Summary',size=35,related='todo_id.summary',readonly=True)
    
    
    