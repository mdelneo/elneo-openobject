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

class account_invoice_line(models.Model):
    _inherit = "account.invoice.line"
    
    cost_price = fields.Float('Cost Price', digits=(16, 2))
    
    @api.one
    def write(self,vals):
        if vals.get('product_id', False):
            product = self.env['product.product'].browse(vals['product_id'])
            self.cost_price = product.standard_price
        
        return super(account_invoice_line,self).write(vals)
            
    @api.model        
    def create(self,vals):
        if vals.get('product_id',False):
            product = self.env['product.product'].browse(vals['product_id'])
            vals['cost_price'] = product.standard_price
        return super(account_invoice_line, self).create(vals)