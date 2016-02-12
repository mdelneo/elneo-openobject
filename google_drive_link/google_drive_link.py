from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
from openerp import models,fields,api
from operator import itemgetter
import re
from openerp import _


class product_category_drive_link(models.Model):
    _name = 'product.category.drive.link'
    
    @api.model
    def _lang_get(self):
        obj = self.env['res.lang']
        res = obj.search([])
        return [(r.code, r.name) for r in res] + [('','')]
    
    name = fields.Char('Name') 
    product_category_id = fields.Many2one('product.category', string='Category')
    link = fields.Char('Url')
    lang = fields.Selection(_lang_get, 'Language', size=32)
    
product_category_drive_link()


class product_drive_link(models.Model):
    _name = 'product.drive.link'
    
    @api.model
    def _lang_get(self):
        obj = self.env['res.lang']
        res = obj.search([])
        return [(r.code, r.name) for r in res] + [('','')]
    
    
    name = fields.Char('Name') 
    product_id = fields.Many2one('product.product', string='Product')
    link = fields.Char('Url')
    lang = fields.Selection(_lang_get, 'Language', size=32)
    
product_drive_link()    

class product_product(models.Model):
    _inherit = 'product.product'
    
    drive_links = fields.One2many('product.drive.link', 'product_id', string='Drive links')
    
product_product()

class product_category(models.Model):
    _inherit = 'product.category'
    
    drive_links = fields.One2many('product.category.drive.link', 'product_category_id', string='Drive links')
    
product_category()