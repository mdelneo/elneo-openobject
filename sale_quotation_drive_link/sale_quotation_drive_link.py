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
        
    @api.one
    def compute_name(self):
        self.name = self.get_drive_link().name 
    
    name = fields.Char('Name',size=255,compute='compute_name')
    sale_order_id = fields.Many2one('sale.order', 'Sale order')    
    product_category_drive_link_id = fields.Many2one('product.category.drive.link', 'Drive link (category)')
    product_drive_link_id = fields.Many2one('product.category.drive.link', 'Drive link (product)')
    sale_line_id = fields.Many2one('sale.order.line', 'Sale order line')
    
sale_drive_link()

class sale_order(models.Model):
    _inherit = 'sale.order'

    display_drive_links = fields.Boolean("Display documentation links")
    drive_links = fields.One2many('sale.drive.link', 'sale_order_id', 'Drive links')
    
    @api.onchange('order_line')
    def on_change_order_lines(self):
        drive_links = []
        for order_line in self.order_line:
            #create drive links from product_drive_links
            for drive_link in order_line.product_id.drive_links:
                drive_links.append(
                    {
                     'sale_order_id':self.id, 
                     'product_drive_link_id':drive_link.id,
                     'sale_line_id':order_line.id
                    }                   
                )
                
            for drive_link in order_line.product_id.get_product_category_drive_links():
                drive_links.append(
                    {
                     'sale_order_id':self.id, 
                     'product_category_drive_link_id':drive_link.id,
                     'sale_line_id':order_line.id
                    }
                )
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
