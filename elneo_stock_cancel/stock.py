# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2016 Elneo
#                        http://www.elneo.com
#    
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
from datetime import datetime

from openerp import tools


class stock_picking(models.Model):
    _inherit = 'stock.picking'


    @api.multi
    def action_revert_done(self):
        for picking in self:
            
            for move in picking.move_lines:
                quants = self.env['stock.quant'].search([('history_ids','in',[move.id]),('location_id','=',move.location_dest_id.id)])
                
                if quants:
                    for quant in quants.sudo():
                        # The found quant quantity is available
                        if quant.qty == move.product_qty:
                            quant.location_id = move.location_id
                            quant.reservation_id = False
                        # The found quant quantity is greater than move quantity
                        # We split quant and update quantities
                        elif quant.qty > move.product_qty:
                            quant_copy = quant.copy()
                            quant_copy.location_id = move.location_id
                            quant_copy.qty = move.product_qty
                            quant.qty -= move.product_qty
                        # The found quant quantity is smaller than the move quantity
                        # We transfer the whole quant to the former location
                        # And we create a new quant for the rest quantity
                        elif quant.qty < move.product_qty:
                            quant_copy = quant.copy()
                            quant.location_id = move.location_id
                            quant_copy.qty = move.product_qty - quant.qty
                else:
                    # Quant does not exist or has been already transfered completely
                    dest_quant_vals = {
                        'product_id': move.product_id.id,
                        'location_id': move.location_dest_id.id,
                        'qty': -move.product_qty,
                        'cost': move.price_unit,
                        'in_date': datetime.now().strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),
                        'company_id': move.company_id.id,

                    }
                    origin_quant_vals = {
                        'product_id': move.product_id.id,
                        'location_id': move.location_id.id,
                        'qty': move.product_qty,
                        'cost': move.price_unit,
                        'in_date': datetime.now().strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),
                        'company_id': move.company_id.id,
                        
                    }
                    self.env['stock.quant'].sudo().create(dest_quant_vals)
                    self.env['stock.quant'].sudo().create(origin_quant_vals)
                    
                move.state = 'draft'    
                        
            picking.state = 'draft'
            
            picking.delete_workflow()
            picking.create_workflow()
        
            picking.message_post(
            _("The picking has been re-opened and set to draft state. Stock Quantities have been set to original ones."))
            
            
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
