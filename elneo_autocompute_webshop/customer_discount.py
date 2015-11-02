from openerp import models,fields,api
from openerp.tools.float_utils import float_compare, float_round
from datetime import datetime
from openerp.exceptions import except_orm, AccessError, MissingError, ValidationError
import logging
import sys
from operator import itemgetter, attrgetter
from pygments.lexer import _inherit


class product_template(models.Model):
    _inherit = 'product.template'
    
    @api.one
    def _get_is_pneumatics(self):
        is_pneumatics = False 
        if self.web_shop_product or self.categ_dpt in ('Pneumatics','Hydraulics'):
            is_pneumatics = True
        self.is_pneumatics = is_pneumatics
    
    def get_customer_sale_price(self, discount_type_id, sale_price, cost_price, quantity):
        if self.web_shop_product and self.product_group_id:
            
            purchase_price = self.get_purchase_public_price(quantity)['purchase_price']
            
            #apply additional discount "product group discount" object 
            if discount_type_id:
                #....and use_discount_type
                discount_type = self.env['product.discount.type'].browse(discount_type_id)
                
                discount_percent = 0
                for discount_type_value in discount_type.product_group_discounts:
                    if discount_type_value.product_group_id.id == self.product_group_id.id:
                        discount_percent = discount_type_value.discount
                        break
                sale_price = sale_price - (sale_price * (discount_percent/100))
            
            #get final price depending on minimum margin
            if sale_price and purchase_price:
                min_price = purchase_price*self.product_group_id.min_margin_coef
                res = max(sale_price, min_price)
        else:
            res = super(product_template, self).get_customer_sale_price(discount_type_id, sale_price, cost_price, quantity)
        
        return res
    
    is_pneumatics = fields.Boolean('Is pneumatics', compute='_get_is_pneumatics')


class product_discount_type(models.Model):
    _inherit = 'product.discount.type'
    
    product_group_discounts = fields.One2many('product.group.discount', 'discount_type_id', string='Product group discounts')
    

class customer_discount_exception(models.Model):
    _inherit = 'customer.discount.exception'
    product_group_id = fields.Many2one('product.group', 'Product group')
    
    
class product_group_discount(models.Model):
    _name = 'product.group.discount'
    _rec_name = 'discount'
    _order = 'discount_type_id, product_group_id'  
    
    discount_type_id = fields.Many2one('product.discount.type', 'Discount type')
    product_group_id = fields.Many2one('product.group', 'Product group')
    discount = fields.Float('Discount (%)')
    
product_group_discount()
