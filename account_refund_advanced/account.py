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

class AccountMoveReconcile(models.Model):
    _inherit='account.move.reconcile'
    
    @api.multi
    def unlink(self):
        if len(self.mapped('line_id').filtered(lambda r:r.account_id.not_refund_auto_rec != True)) > 0:
            return super(AccountMoveReconcile,self).unlink()
        else:
            return True
        
class AccountAccount(models.Model):
    _inherit='account.account'
    
    not_refund_auto_rec=fields.Boolean(string='No reconciliation when refund')
    
    
class AccountMoveLine(models.Model):
    _inherit='account.move.line'
    
    @api.model
    def _get_move_from_reconcile(self,ids):
        if not self.env.get('from_refund',False):
            return super(AccountMoveLine,self)._get_move_from_reconcile(ids)
        
        move = {}
        for r in self.env['account.move.reconcile'].browse(ids):
            for line in r.line_partial_ids.filtered(lambda r:r.account_id.not_refund_auto_rec != True):
                move[line.move_id.id] = True
            for line in r.line_id.filtered(lambda r:r.account_id.not_refund_auto_rec != True):
                move[line.move_id.id] = True
        move_line_ids = []
        if move:
            move_line_ids = self.env['account.move.line'].search([('move_id','in',move.keys())])
        return move_line_ids
    

class AccountInvoiceRefund(models.TransientModel):
    _inherit='account.invoice.refund'
    
    filter_refund = fields.Selection([('refund', _('Create a refund to be modified (without cancelling original invoice)')), ('cancel', _('Cancel: create a non editable refund that cancel original invoice')),('modify', _('Modify: create a non editable refund that cancel original invoice and create a new draft invoice'))])
    
    @api.multi
    def compute_refund(self,mode='refund'):
        return super(AccountInvoiceRefund,self.with_context(from_refund=True)).compute_refund(mode=mode)
        
