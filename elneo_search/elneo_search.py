# -*- coding: utf-8 -*-
from openerp import models,fields,api


class product_product(models.Model):
    _inherit = 'product.product'
    
    search_field_layout = fields.Char(related='product_tmpl_id.search_field_layout', size=4096, string='Advanced search')

product_product()

class product_template(models.Model):
    _inherit = 'product.template'
    
    @api.multi
    def get_ext_name(self):
        result = {}
        for product_id in self:                    
            result[product_id] = ''
        return result 
    
    @api.multi
    def search_ext_name(self, operator, value):
        self._cr.execute("select product_tmpl_id from product_search_column('"+value+"');")
        res = self._cr.fetchall()
        return [('id', 'in', [x[0] for x in res])]
    
    search_field_layout = fields.Char(compute='get_ext_name', search=search_ext_name, size=4096, string='Advanced search')
product_product()