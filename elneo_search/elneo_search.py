# -*- coding: utf-8 -*-
from openerp import models,fields,api, _
from openerp.exceptions import ValidationError
import re
import inspect, os
from subprocess import call


class elneo_search(models.TransientModel):
    _name = 'elneo.search'
    
    @api.model
    def _install_sql(self):
        sql_files = [
            #open('/'.join(__file__.split('/')[:-1])+'/data/install_product_search.sql'),
            open('/'.join(__file__.split('/')[:-1])+'/data/install_partner_search.sql'),
        ]
        for sql_file in sql_files:
            sql_query = sql_file.read()
            self._cr.execute(sql_query)

class product_product(models.Model):
    _inherit = 'product.product'
    
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
            else:
                products = self.search([('search_field_layout','ilike',name)], limit=limit)
        else:
            products = self.search(args, limit=limit)
        return products.name_get()
    
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
    
    search_field_layout = fields.Char(compute='get_ext_name', search=search_ext_name, size=4096, string='Advanced search')
    search_default_code_layout = fields.Char(compute='get_ext_name', search=search_default_code, size=4096, string='Code')

product_product()


class res_partner(models.Model):
    _inherit = 'res.partner'
    
    @api.multi
    def get_ext_name(self):
        result = {}
        for product_id in self:                    
            result[product_id] = ''
        return result
     
    @api.multi
    def search_ext_name(self, operator, value):
        self._cr.execute("select id from partner_search_column('"+value+"');")
        res = self._cr.fetchall()
        return [('id', 'in', [x[0] for x in res])]
  
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not args:
            args=[]
        if name:
            if len(name) < 3:
                partners = self.search([('ref','=',name)]+ args, limit=limit)
            else:
                partners = self.search([('search_field_layout','ilike',name)], limit=limit)
        else:
            partners = self.search(args, limit=limit)
        return partners.name_get()
    
    search_field_layout = fields.Char(compute='get_ext_name', search=search_ext_name, size=4096, string='Advanced search')
    
res_partner()