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

from openerp import models, fields,api

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    @api.model
    def _prepare_order_line_invoice_line(self, line, account_id=False):
        res = super(sale_order_line,self)._prepare_order_line_invoice_line(line, account_id)
        res['cost_price'] = line.purchase_price
        return res

class stock_move(models.Model):
    _inherit = 'stock.move'
    
    @api.model
    def _create_invoice_line_from_vals(self, move, invoice_line_vals):
        if move.procurement_id and move.procurement_id.sale_line_id:
            invoice_line_vals['cost_price'] = move.procurement_id.sale_line_id.purchase_price
        elif move.product_id:
            invoice_line_vals['cost_price'] = move.product_id.standard_price
            
        res = super(stock_move,self)._create_invoice_line_from_vals(move, invoice_line_vals)
        return res

class account_invoice_line(models.Model):
    _inherit = "account.invoice.line"
    
    cost_price = fields.Float('Cost Price', digits=(16, 2))
    