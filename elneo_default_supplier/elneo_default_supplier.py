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
from openerp import models,fields,api
   
class product_template(models.Model):
    _inherit = "product.template"
    
    @api.multi
    @api.depends('seller_ids')
    def get_default_supplier(self):
        for product in self:
            if len(product.seller_ids) == 1:
                product.default_supplier_id = product.seller_ids[0].name.id
            elif len(product.seller_ids) > 1:
                min_seq = min([suppinfo.sequence for suppinfo in product.seller_ids])
                for suppinfo in product.seller_ids:
                    if suppinfo.sequence == min_seq:
                        product.default_supplier_id = suppinfo.name.id
            else:
                product.default_supplier_id = None
    
    @api.multi
    def get_default_supplierinfo(self):
        for product in self:
            if len(product.seller_ids) == 1:
                product.default_supplierinfo_id = product.seller_ids[0].id
            elif len(product.seller_ids) > 1:
                min_seq = min([suppinfo.sequence for suppinfo in product.seller_ids])
                for suppinfo in product.seller_ids:
                    if suppinfo.sequence == min_seq:
                        product.default_supplierinfo_id = suppinfo.id
            else:
                product.default_supplierinfo_id = None
    
    def _get_product_by_supplierinfo(self, cr, uid, ids, context=None):
        result = []
        for orderpoint in self.pool.get("product.supplierinfo").browse(cr, uid, ids, context):
            result.append(orderpoint.product_id.id)
        return result
    
    default_supplier_id = fields.Many2one('res.partner', 'Default supplier', compute=get_default_supplier,readonly=True, store=True)
    default_supplierinfo_id = fields.Many2one('product.supplierinfo', 'Default supplier', compute=get_default_supplierinfo, readonly=True)


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    #'default_supplier_id':fields.related("product_id","product_tmpl_id", "default_supplier_id", type="many2one", relation="res.partner", string="Default supplier", readonly=True),
    
    default_supplier_id = fields.Many2one('res.partner',related='product_id.product_tmpl_id.default_supplier_id',readonly=True,string='Default Supplier')

    