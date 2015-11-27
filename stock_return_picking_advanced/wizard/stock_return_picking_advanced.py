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
import openerp.addons.decimal_precision as dp

class StockReturnPickingLine(models.TransientModel):
    _inherit = 'stock.return.picking.line'

    qty_already_returned = fields.Float(string="Quantity already returned",digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True)

class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'
    
    already_returned = fields.Boolean(string='Already Returned',help='Technical field to help to know if products are already returned')
    
    @api.model
    def default_get(self,fields):
        res = super(StockReturnPicking,self).default_get(fields=fields)

        result1=[]
        pick = self.env['stock.picking'].browse(self.env.context.get('active_ids',False))
       
        if pick:
           
            already=False
            for move in pick.move_lines:
                
                #Sum the quants in that location that can be returned (they should have been moved by the moves that were included in the returned picking)
                qty = 0
                quants = self.env['stock.quant'].search([('history_ids', 'in', move.id), ('qty', '>', 0.0), ('location_id', 'child_of', move.location_id.id)])
                for quant in quants:
                    qty += quant.qty
                qty = self.env['product.uom']._compute_qty(move.product_id.uom_id.id, qty, move.product_uom.id)
                if qty > 0 :
                    already = True
                    
                result1.append({'qty_already_returned': qty, 'move_id': move.id})

            if len(result1) > 0:
                res1=[]
                if 'product_return_moves' in fields:
                    for product_return_move in res['product_return_moves']:
                        for result in result1:
                            if result['move_id'] == product_return_move['move_id']:
                                product_return_move['qty_already_returned'] = result['qty_already_returned']
                                
                        res1.append(product_return_move)
                
                    res.update({'product_return_moves' : res1,'already_returned':already}) 
        
        return res
    
  
    @api.multi
    def _create_returns(self):        
        self.ensure_one()
        
        return_valid_auto = self.env['ir.config_parameter'].get_param('stock_return_picking_advanced.return_valid_auto',False)

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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
