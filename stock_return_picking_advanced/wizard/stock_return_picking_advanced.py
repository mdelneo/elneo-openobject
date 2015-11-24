# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from openerp import models, api, _


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'
  
    @api.multi
    def _create_returns(self):
        res = {}
        self.ensure_one()
        
        return_valid_auto = self.env['ir.config_parameter'].get_param('stock_return_picking_advanced.return_valid_auto',False)
        return_create_invoice = self.env['ir.config_parameter'].get_param('stock_return_picking_advanced.return_create_invoice',False)
        if return_valid_auto == 'True':
            new_picking_id, pick_type_id = super(StockReturnPicking,self.with_context(advanced_picking=True))._create_returns()
            picking =  self.env['stock.picking'].browse(new_picking_id)
            picking.force_assign()
            picking.action_done()
        else:
            new_picking_id, pick_type_id = super(StockReturnPicking,self.with_context(advanced_picking=True))._create_returns()
 
        return new_picking_id, pick_type_id
         
    
    @api.multi
    def create_returns(self):
        res = {}
        self.ensure_one()
        
        return_create_invoice = self.env['ir.config_parameter'].get_param('stock_return_picking_advanced.return_create_invoice',False)
            
        if return_create_invoice == "True":
            picking_id, pick_type_id = self._create_returns()
            wizard = self.env['stock.invoice.onshipping'].with_context(active_ids=[picking_id]).create({})
            invoice_id = wizard.create_invoice()
            if (isinstance(invoice_id,list)) and len(invoice_id) > 0:
                invoice_id = invoice_id[0]
            
            return {
                'type': 'ir.actions.act_window',
                'name': _('Invoice'),
                'res_model': 'account.invoice',
                'res_id': invoice_id, #If you want to go on perticular record then you can use res_id 
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'self',
                'nodestroy': True,
                }

        return super(StockReturnPicking,self).create_returns()
  
           
class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    @api.one
    def copy(self,default=None):
        if default == None:
            default={}
        if self.env.context.get('advanced_picking',False):
            default.update({'name':self.name+'-return'})
            
        return super(StockPicking,self).copy(default)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
