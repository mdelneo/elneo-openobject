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
        if discount_type_id and sale_price and self.is_pneumatics:
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
    
    
    @api.multi
    def onchange_partner_id(self, partner):
        result = super(sale_order, self).onchange_partner_id(partner)
        if not result:
            result = {'value':{}}
        elif not result.has_key('value'):
            result['value'] = {}
            
        partner_obj = self.env["res.partner"].browse(partner)
        
        result['value'].update({'discount_type_id':partner_obj.discount_type_id.id})
        
        return result
    
    
    #@api.onchange('discount_type_id') -- don't know why it doesn't works
    @api.one
    def update_all_prices(self):
        for line in self.order_line:
            on_change_res = line.product_id_change_with_wh_quotation_address_discount_type(
                pricelist=self.pricelist_id.id, 
                product=line.product_id.id, 
                qty=line.product_uom_qty, 
                uom=line.product_uom.id,  
                discount_type_id=self.discount_type_id.id, 
                partner_id=self.partner_id.id
            )
            
            
            if on_change_res.has_key('value'):
                if on_change_res['value'].has_key('purchase_price'):    
                    line.purchase_price = on_change_res['value']['purchase_price']
                if on_change_res['value'].has_key('brut_sale_price'):    
                    line.brut_sale_price = on_change_res['value']['brut_sale_price']
            #For Sale price, we get customer price
            customer_price = line.product_id.get_customer_sale_price(self.discount_type_id.id, line.product_id.list_price, line.product_id.cost_price, line.product_uom_qty)
            product_price = line.product_id.list_price
            discount = 100-(100*customer_price/product_price)
            line.price_unit = product_price
            line.discount = discount
            
        
sale_order()

class res_partner(models.Model):
    _inherit = 'res.partner' 
    discount_type_id = fields.Many2one('product.discount.type', string='Discount type')
    discount_exceptions = fields.One2many('customer.discount.exception','partner_id','Discount exceptions')
res_partner()


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    @api.model
    def _calc_line_base_price(self, line):
        return line.price_unit
    
    @api.one
    @api.onchange('discount')
    def update_price_unit(self):
        #prevent loop
        if round(self.brut_sale_price - (self.brut_sale_price*self.discount/100)) == round(self.price_unit):
            return
        new_price_unit = self.brut_sale_price - (self.brut_sale_price*self.discount/100)
        self.price_unit = new_price_unit
        
    
    @api.one
    @api.onchange('price_unit')
    def update_discount(self):
        #prevent loop
        if round(self.brut_sale_price - (self.brut_sale_price*self.discount/100)) == round(self.price_unit):
            return
        if self.brut_sale_price:
            new_discount = 100 - (self.price_unit / self.brut_sale_price) * 100
        else:
            new_discount = 0
        self.discount = new_discount
    
    
    @api.multi
    def product_id_change_with_wh_quotation_address_discount_type(self, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, warehouse_id=False, quotation_address_id=False, discount_type_id=False):
        
        #for pneumatics product, don't use price list. Discount is computed in get_customer_sale_price function below via discount type.
        product_obj = self.env['product.product'].browse(product)
        if product_obj and product_obj.is_pneumatics:
            pricelist = 1
        
        res = super(sale_order_line, self).product_id_change_with_wh_quotation_address(pricelist, product, qty=qty,
                uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
                lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, warehouse_id=warehouse_id, quotation_address_id=quotation_address_id)
        
        if res.has_key('value') and res['value'].has_key('price_unit') and res['value'].has_key('purchase_price'):
            product = self.env['product.product'].browse(product)
            customer_price = product.get_customer_sale_price(discount_type_id, res['value']['price_unit'], res['value']['purchase_price'], qty)
            product_price = product.list_price
            if product_price:
                discount = 100-(100*customer_price/product_price)
            else:
                discount = 0
            res['value']['price_unit'] = customer_price
            res['value']['discount'] = discount
            
        return res
    
    @api.multi
    def product_uom_qty_change_with_wh_discount_type(self, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, warehouse_id=False, discount_type_id=False):
        
        res = {}
        #change price of pneumatics products when qty change
        product_obj = self.env['product.product'].browse(product)
        if product_obj and product_obj.is_pneumatics:
            pricelist = 1
            res = self.product_id_change_with_wh_quotation_address_discount_type(pricelist, product, qty=qty,
                    uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
                    lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, warehouse_id=warehouse_id, quotation_address_id=False, discount_type_id=discount_type_id)
        
        #don't change route type when change qty
        if res.get('value') and res['value'].get('route_id'):
            res['value'].pop('route_id')
                
        return {}
      
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
