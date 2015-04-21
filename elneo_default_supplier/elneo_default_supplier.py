# -*- encoding: utf-8 -*-
from openerp import models,fields,api
from openerp.tools.float_utils import float_compare, float_round
from datetime import datetime
from openerp.exceptions import except_orm, AccessError, MissingError, ValidationError
import logging
import sys
from operator import itemgetter, attrgetter
from pygments.lexer import _inherit

    
class product_template(models.Model):
    _inherit = "product.template"
    
    @api.multi
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
    
    default_supplier_id = fields.Many2one('res.partner', 'Default supplier', compute=get_default_supplier, method=True,readonly=True)
    default_supplierinfo_id = fields.Many2one('product.supplierinfo', 'Default supplier', compute=get_default_supplierinfo, method=True, readonly=True)
    
product_template()


class sale_order(models.Model):
    _inherit = 'sale.order.line'
    
    #'default_supplier_id':fields.related("product_id","product_tmpl_id", "default_supplier_id", type="many2one", relation="res.partner", string="Default supplier", readonly=True),
    
    default_supplier_id = fields.Many2one('res.partner',related='product_id.product_tmpl_id.default_supplier_id',readonly=True,string='Default Supplier')
    
sale_order()
    