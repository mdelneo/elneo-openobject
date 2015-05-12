from openerp import models,fields,api
from openerp.tools.float_utils import float_compare, float_round
from datetime import datetime
from openerp.exceptions import except_orm, AccessError, MissingError, ValidationError
import logging
import sys
from operator import itemgetter, attrgetter
from pygments.lexer import _inherit


#INHERITANCE MODELS

class product_product(models.Model):
    _inherit = 'product.product'
    
    def get_customer_sale_price(self, discount_type, sale_price, cost_price, quantity):
        return self.product_tmpl_id.get_customer_sale_price(discount_type, sale_price, cost_price, quantity)

class product_template(models.Model):
    _inherit = 'product.template'
    
    def get_customer_sale_price(self, discount_type_id, sale_price, cost_price, quantity):
        
        '''
        is_pneumatics = False 
        if self.web_shop_product or self.categ_dpt in ('Pneumatics','Hydraulics'):
            is_pneumatics = True
        '''
        is_pneumatics = True
        
        if discount_type_id and sale_price and is_pneumatics:
            margin_percent = ((sale_price - cost_price)/sale_price)*100
            if margin_percent < 0:
                margin_percent = 0
            if margin_percent > 100:
                margin_percent = 100
            margin_percent = round(margin_percent,2)
            discounts = self.env['discount.type.discount'].search([('discount_type_id','=',discount_type_id),('margin_min','<=',margin_percent),('margin_max','>=',margin_percent)])
            if discounts:
                sale_price = sale_price-((discounts[0].discount_percent/100)*sale_price)
        
        return sale_price

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    discount_type_id  = fields.Many2one('product.discount.type', 'Discount type', states={'draft': [('readonly', False)]})
    
    
    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        result = super(sale_order, self).onchange_partner_id(cr, uid, ids, part, context)
        if not result:
            result = {'value':{}}
        elif not result.has_key('value'):
            result['value'] = {}
            
        partner = self.pool.get("res.partner").browse(cr, uid, part)
        
        result['value'].update({'discount_type_id':partner.discount_type_id.id})
        
        return result
        
sale_order()

class res_partner(models.Model):
    _inherit = 'res.partner' 
    discount_type_id = fields.Many2one('product.discount.type', string='Discount type')
    discount_exceptions = fields.One2many('customer.discount.exception','partner_id','Discount exceptions')
res_partner()


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, discount_type_id=False, context=None):
        res = super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty=qty,
                uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
                lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, context=context)
        if res.has_key('value') and res['value'].has_key('price_unit') and res['value'].has_key('purchase_price'):
            res['value']['price_unit'] = self.pool.get('product.product').browse(cr, uid, product, context).get_customer_sale_price(discount_type_id, res['value']['price_unit'], res['value']['purchase_price'], qty)
        
        return res
      
#BASE MODELS

class discount_type_discount(models.Model):
    _name = 'discount.type.discount'
    _order = 'discount_type_id, margin_min, margin_max' 
    
    discount_type_id = fields.Many2one('product.discount.type', string="Discount type")
    margin_max = fields.Float(string="Maximum margin")
    margin_min = fields.Float(string="Minimum margin")
    discount_percent = fields.Float(string="Discount (percent)")
    
discount_type_discount()


class product_discount_type(models.Model):
    _name = 'product.discount.type'
    _order = 'name'
    
    name = fields.Char(string="name")
    discounts = fields.One2many('discount.type.discount', 'discount_type_id', string='Discounts')
    
    #product_group_discounts = fields.One2many('product.group.discount', 'discount_type_id', string='Product group discounts')
    #to copy in new module

product_discount_type()

class customer_discount_exception(models.Model):
    _name = 'customer.discount.exception'
    _order = 'partner_id, categ_id, discount'
    
    partner_id = fields.Many2one('res.partner', 'Partner')
    categ_id = fields.Many2one('product.category', 'Product category')
    discount = fields.Float('Discount')
    #product_group_id = fields.Many2one('product.group', 'Product group')
    #to copy in new module
    
customer_discount_exception()
