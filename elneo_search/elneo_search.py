# -*- coding: utf-8 -*-
from openerp import models,fields,api
from openerp.exceptions import ValidationError
import re


class product_product(models.Model):
    _inherit = 'product.product'
    
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not args:
            args=[]
        
        if name:
            if len(name) < 3:
                products = self.search([('default_code','=',name)]+ args, limit=limit)
            else:
                products = self.search([('search_field_layout','ilike',name)], limit=limit)
        else:
            products = self.search(args, limit=limit)            
        return products.name_get()
    
    search_field_layout = fields.Char(related='product_tmpl_id.search_field_layout', size=4096, string='Advanced search')
    search_default_code_layout = fields.Char(related='product_tmpl_id.search_default_code_layout', size=4096, string='Code')

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
        self._cr.execute("select id from product_search_column('"+value+"');")
        res = self._cr.fetchall()
        return [('id', 'in', [x[0] for x in res])]
    
    @api.multi
    def search_default_code(self, operator, value):
        self._cr.execute("select id from product_search_code('"+value+"');")
        res = self._cr.fetchall()
        return [('id', 'in', [x[0] for x in res])]
    
    
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not args:
            args=[]
        
        if name:
            matches = False
            if name and name[0] == '[':
                #if pattern begin with [ : we consider it as well formated, and we limit search with the exact code extracted between []
                matches = re.findall("\[([^\]]*)\]*",name)
            if matches:
                products = self.search([('default_code','=',matches[0])]+ args, limit=limit)
            elif len(name) < 3:
                products = self.search([('default_code','=',name)]+ args, limit=limit)
                if not products:
                    raise ValidationError(_('You must type a minimum of 3 characters to search a product'))
            else:
                products = self.search([('search_field_layout','ilike',name)], limit=limit)
        else:
            products = self.search(args, limit=limit)
        return products.name_get()
    
    
    
    search_field_layout = fields.Char(compute='get_ext_name', search=search_ext_name, size=4096, string='Advanced search')
    search_default_code_layout = fields.Char(compute='get_ext_name', search=search_default_code, size=4096, string='Code')
    
    
product_template()