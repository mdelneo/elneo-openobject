from openerp import models,fields,api
from openerp.tools.float_utils import float_compare, float_round
from datetime import datetime
from openerp.exceptions import except_orm, AccessError, MissingError, ValidationError
import logging
import sys
from operator import itemgetter, attrgetter
import openerp.addons.decimal_precision as dp



class product_group(models.Model):
    _name = 'product.group'
    _order = 'name'
    
    name = fields.Char(size=255, string='Name')
    description = fields.Char(size=255, string='Description', translate=True) 
    coeff_sale_price = fields.Float(string='Coefficient', help="Coefficient between public price and sale price", default=1) 
    min_margin_coef = fields.Float(string='Minimum margin coef.', help="Minimum coefficient between Landefeld purchase price and sale price", default=1.25)
    web_shop_price_base = fields.Selection([('public_price','Public price'),('purchase_price','Purchase price')], 'Web shop price base', default='public_price')
    
product_group()

class pricelist_partnerinfo(models.Model):
    _inherit = "pricelist.partnerinfo"
    
    public_price = fields.Float('Public Price', digits=dp.get_precision('Purchase Price'))
pricelist_partnerinfo()

class product_template(models.Model):
    _inherit = "product.template"
    
    product_group_id = fields.Many2one('product.group', 'Product group')
    web_shop_product = fields.Boolean("Web shop product")
    
    def get_purchase_public_price(self, quantity):
        public_price = 0
        purchase_price = 0
        for supplier_info in self.seller_ids:
            if not public_price and supplier_info.name.id == 4509:
                #get prices order by min quantity
                prices = [(pricelist.min_quantity, pricelist.public_price, pricelist.price) for pricelist in supplier_info.pricelist_ids] #replace with displayed_pricelist_ids when displayed_pricelist_ids exists
                prices = sorted(prices, key=itemgetter(0))
                
                #use price for min quantity, or price for quantity specified by parameter
                if prices:
                    public_price = prices[0][1]
                    purchase_price = prices[0][2]
                else:
                    public_price = 0
                    purchase_price = 0
                
                if quantity:
                    for price in prices:
                        if price[0] <=quantity:
                            public_price = price[1]
                            purchase_price = price[2]
                        else:
                            break;
                break;
        return {'purchase_price':purchase_price,'public_price':public_price}
    
    #When cost_price computation will be ok, we can use cost_price instead of standard_price
    @api.one
    def get_sale_price(self, quantity=0):
        res = 0
        
        if self.web_shop_product and self.product_group_id:
            purchase_public_price = self.get_purchase_public_price(quantity)
            public_price = purchase_public_price['public_price']
            purchase_price = purchase_public_price['purchase_price'] 
                
            if not self.compute_sale_price:
                computed_price = max(self.sale_price_fixed, self.sale_price_seller)
            else:
                #computed price : price with discount of product group                
                if self.product_group_id.web_shop_price_base == 'purchase_price' and purchase_price:
                    computed_price = purchase_price*self.product_group_id.coeff_sale_price
                elif public_price:
                    computed_price = public_price*self.product_group_id.coeff_sale_price
                else:
                    computed_price = 0
                    
            if computed_price and purchase_price:
                min_price = purchase_price*self.product_group_id.min_margin_coef
                return max(computed_price, min_price)
        else:
            res = super(product_template, self).get_sale_price(quantity)
            
        return res
    
    @api.depends('categ_id','standard_price','web_shop_product','product_group_id')
    def _get_list_price(self):
        return super(product_template, self)._get_list_price()
    
product_template()