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
from openerp import models, fields, api, _
from datetime import datetime

class MaintenanceTodo(models.Model):
    _name = 'maintenance.todo'
    _rec_name='code'
    
    _inherit=['mail.thread','ir.needaction_mixin']
    
    @api.multi
    def _get_code(self):
        return self.env['ir.sequence'].get('maintenance.todo')
    
    @api.one
    def copy(self,default=None):
        new_todo = super(MaintenanceTodo, self).copy(default)
        new_todo.code = self.env['ir.sequence'].get('maintenance.todo')
        
    @api.model
    def _needaction_domain_get(self):
        return [('assigned_user_id','=', self.env.uid),('state','=', 'progress')]
    
    description = fields.Text('Description',size=255,required=True)
    code = fields.Char("Code", size=20, index=True, required=True,default=_get_code)
    installation_id = fields.Many2one('maintenance.installation',string='Installation',required=True)
    state = fields.Selection([('asked','Asked'),('progress','In progress'),('assigned','Assigned'),('done','Done'),('cancel','Cancelled')],string="State",required=True,default='asked',track_visibility='onchange')
    intervention_from_id=fields.Many2one('maintenance.intervention',string='Intervention From')
    intervention_assign_id=fields.Many2one('maintenance.intervention',string='Intervention assigned to',track_visibility='onchange')
    ask_user_id=fields.Many2one('res.users',string='Claim User',default=lambda obj: obj.env.user)
    assigned_user_id=fields.Many2one('res.users',string='Assigned User',track_visibility='onchange')
    done_user_id=fields.Many2one('res.users',string='Done User',track_visibility='onchange')
    ask_date=fields.Datetime('Ask Date',default=lambda *a : datetime.today().strftime('%Y-%m-%d %H:%M:%S'),readonly=True )
    done_date=fields.Datetime('Done Date',readonly=True)
    
    
    @api.one
    def action_assign(self):
        self.state = 'assigned'
        
    @api.one
    def action_progress(self):
        self.state = 'progress'
        
    @api.one
    def action_cancel(self):
        self.state = 'cancel'
        
    @api.one
    def action_done(self):
        self.state = 'done'
        
    @api.one
    def action_asked(self):
        self.state = 'asked'
        
    @api.multi
    def action_assign_to(self):
        context = self.env.context.copy()
        return {
            'name':_("Assign Todo"),
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'maintenance.todo.assign.to',
            #'res_id': partial_id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': context
        }
        
    @api.one
    def action_progress_my(self):
        self.assigned_user_id = self.env.user
        self.action_progress()
        
        
class maintenance_installation(models.Model):
    _inherit='maintenance.installation'
    
    todo_ids = fields.One2many('maintenance.todo','installation_id',string='Todo\'s')
    
class maintenance_intervention(models.Model):
    _inherit = 'maintenance.intervention'
    
    @api.multi
    def add_todo(self):
        context = self.env.context.copy()
        return {
            'name':_("Add Todo"),
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'maintenance.todo.add',
            #'res_id': partial_id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': context
        }
    
    @api.one
    def _get_todos(self):
        self.todo_ids = self.env['maintenance.todo'].search([('installation_id','=',self.installation_id.id)]) - self.todo_assigned_ids
    
    todo_assigned_ids = fields.One2many('maintenance.todo','intervention_assign_id',string="Assigned Todo's")
    
    todo_ids = fields.One2many(comodel_name='maintenance.todo',compute=_get_todos,string="Todo's")
    
    
    
    @api.multi
    def action_confirm(self):
        
            return super(maintenance_intervention,self).action_confirm()
