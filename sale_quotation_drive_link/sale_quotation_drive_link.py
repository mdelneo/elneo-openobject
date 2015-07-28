from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
from openerp import models,fields,api
from operator import itemgetter
import re


class sale_drive_link(models.Model):
    _name = 'sale.drive.link'
    
    def get_drive_link(self):
        if self.product_category_drive_link_id:
            return self.product_category_drive_link_id
        if self.product_drive_link_id:
            return self.product_drive_link_id
        
    name = fields.Char('Name',size=255)
    link = fields.Char('Url',size=255)
    sale_order_id = fields.Many2one('sale.order', 'Sale order')    
    product_category_drive_link_id = fields.Many2one('product.category.drive.link', 'Drive link (category)')
    product_drive_link_id = fields.Many2one('product.category.drive.link', 'Drive link (product)')
    product_ids = fields.Many2many('product.product', 'product_drive_link_rel','drive_link_id','product_id','Products')
    
sale_drive_link()

class sale_order(models.Model):
    _inherit = 'sale.order'

    display_drive_links = fields.Boolean("Display documentation links")
    drive_links = fields.One2many('sale.drive.link', 'sale_order_id', 'Drive links')
    
    @api.onchange('order_line')
    def on_change_order_lines(self):
        def _drive_link_contains_cat(product_category_drive_link_id):
            for drive_link in drive_links:
                if drive_link.get('product_category_drive_link_id',0) == product_category_drive_link_id:
                    return drive_link
            return False
        
        def _drive_link_contains_prod(product_drive_link_id):
            for drive_link in drive_links:
                if drive_link.get('product_drive_link_id',0) == product_drive_link_id:
                    return drive_link
            return False
        
        
        drive_links = []
        for order_line in self.order_line:
            #create drive links from product_drive_links
            for drive_link in order_line.product_id.drive_links:
                existing_drive_link = _drive_link_contains_prod(drive_link.id)
                if not existing_drive_link:
                    drive_links.append(
                        {
                         'name':drive_link.name,
                         'link':drive_link.link,
                         'sale_order_id':self.id, 
                         'product_drive_link_id':drive_link.id,
                         'product_ids':[order_line.product_id.id]
                        }                   
                    )
                else:
                    existing_drive_link['product_ids'].append(order_line.product_id.id)
                    
                
            for drive_link in order_line.product_id.get_product_category_drive_links():
                existing_drive_link = _drive_link_contains_cat(drive_link.id)
                if not existing_drive_link:
                    drive_links.append(
                        {
                         'name':drive_link.name,
                         'link':drive_link.link,
                         'sale_order_id':self.id, 
                         'product_category_drive_link_id':drive_link.id,
                         'product_ids':[order_line.product_id.id]
                        }
                    )
                else:
                    existing_drive_link['product_ids'].append(order_line.product_id.id)
                    
        self.drive_links = drive_links
    
sale_order()

class product_product(models.Model):
    _inherit = 'product.product'
    
    def get_product_category_drive_links(self):
        drive_links = []
        cat = self.categ_id
        while cat:
            drive_links.extend(cat.drive_links)
            cat = cat.parent_id
        return drive_links
     
product_product()
