from openerp import models,fields,api
from openerp.tools.float_utils import float_compare, float_round
from datetime import datetime
from openerp.exceptions import except_orm, AccessError, MissingError, ValidationError
import logging
import sys
from operator import itemgetter, attrgetter

class category_coefficientlist(models.Model):
    _name = "elneo_autocompute_saleprice.category_coefficientlist"
    _description = "List of coefficient for partner and product category "
    
    categ_id = fields.Many2one('product.category','Category of Product')
    partner_id = fields.Many2one('res.partner','Partner')
    coefficient = fields.Float('Coefficient', default=1)
    is_brutprice = fields.Boolean('Is Same as Brut Price')
    
    @api.multi
    def action_update_product_sale_price(self):
        product_template_ids = []
        
        logger = logging.getLogger(__name__)
        logger.info('Update product sale price ----- Start Coefficient Update -----')
        
        
        coefficients = self
        total_coefficient = len(coefficients)
        i_coefficient = 0
        begining_coefficient = datetime.now()
        for coefficient in coefficients:
            i_coefficient = i_coefficient + 1   
            timetodoi_coefficient = datetime.now() - begining_coefficient
            todo_coefficient = total_coefficient-i_coefficient
            timeremaining_coefficient = timetodoi_coefficient*todo_coefficient/i_coefficient
                            
            message = unicode(unicode(i_coefficient)+'/'+unicode(total_coefficient)+ ' remaining : '+unicode(timeremaining_coefficient)+ ' current coefficient id: '+unicode(coefficient.id))
            logger.info('Update product sale price -- '+message)
            
            category = coefficient.categ_id
            #By Category and partner
            if coefficient.partner_id and coefficient.categ_id:
                product_template_ids.extend(self.get_product_template_by_category_and_partner(coefficient.categ_id, coefficient.partner_id, category))
 
            #Just by category
            elif not coefficient.partner_id and coefficient.categ_id:
                product_template_ids.extend(self.get_product_template_by_category(coefficient.categ_id, category))
                
            #By category and partner empty
            elif not coefficient.partner_id and not coefficient.categ_id:
                self._cr.execute('WITH  coefficient_by_categories AS ( '\
                           'select categ_id,partner_id from elneo_autocompute_saleprice_category_coefficientlist where categ_id is not null) '\
                           
                           'select distinct product_product.product_tmpl_id as product_template_id from product_product '\
                           'LEFT JOIN product_template '\
                           'LEFT JOIN (product_category p0 '\
                           'LEFT JOIN (product_category p1 '\
                           'LEFT JOIN (product_category p2 '\
                           'LEFT JOIN product_category p3 ON p3.id = p2.parent_id) ON p2.id = p1.parent_id) ON p1.id = p0.parent_id) ON p0.id = product_template.categ_id '\
                           'ON product_product.product_tmpl_id = product_template.id '\
                           'WHERE active '\
                           'AND (p0.id is null or p0.id NOT IN (select categ_id from coefficient_by_categories WHERE (partner_id is null OR partner_id=default_supplier_id))) '\
                           'AND (p1.id is null or p1.id NOT IN (select categ_id from coefficient_by_categories WHERE (partner_id is null OR partner_id=default_supplier_id))) '\
                           'AND (p2.id is null or p2.id NOT IN (select categ_id from coefficient_by_categories WHERE (partner_id is null OR partner_id=default_supplier_id))) '\
                           'AND (p3.id is null or p3.id NOT IN (select categ_id from coefficient_by_categories WHERE (partner_id is null OR partner_id=default_supplier_id)))')
                
                for product_template_id in self._cr.fetchall():
                    product_template_ids.append(product_template_id[0])
                    
        logger.info('Update product sale price -- '+'----- Start Product Update -----')  
        i_product = 0
        begining_product = datetime.now()    
        products_prices = self.pool.get("product.template")._get_list_price(product_template_ids)
        total_product = len(products_prices)
        commit_counter = datetime.now()
        commit_time = 1                 
        for product_template_id in products_prices:         
            i_product = i_product + 1   
            timetodoi_product = datetime.now() - begining_product
            todo_product = total_product-i_product
            timeremaining_product = timetodoi_product*todo_product/i_product
            
            if (datetime.now() - commit_counter).seconds  > commit_time*60:
                commit_counter = datetime.now()
                self._cr.commit()
                logger.info('Update product sale price -- '+'----- Commit -----')
                                
            message = unicode(unicode(i_product)+'/'+unicode(total_product)+ ' remaining : '+unicode(timeremaining_product)+' current product template id : '+unicode(product_template_id))
            logger.info('Update product sale price -- '+message)
            
            self._cr.execute('update product_template set list_price=%s where id=%s', (products_prices[product_template_id],product_template_id,))
            #self.pool.get('product.product').write(cr, uid, product_id, {}, context) 
                
        logger.info('Update product sale price -- ----- End Product Update -----')
        logger.info('Update product sale price -- ----- End Coefficient Update -----')
        ''''''
        return True
    
    def get_product_template_by_category(self, cr, uid, coefficient_category, category):
        product_template_ids = []
        
        if coefficient_category.id !=category.id:
            result = self.search(cr, uid, [ ('categ_id','=',category.id), ('partner_id','=',False)])
            if len(result) > 0:
                return product_template_ids
        
        cr.execute('select product_template.id from product_template '\
                   'where categ_id=%s AND default_supplier_id NOT IN '\
                   '(select partner_id from elneo_autocompute_saleprice_category_coefficientlist where categ_id=%s AND partner_id is not null)', (category.id,category.id))
        for product_template_id in cr.fetchall():
            product_template_ids.append(product_template_id[0])
        
        for subCategory in category.child_id:
            product_template_ids.extend(self.get_product_template_by_category(cr, uid, coefficient_category, subCategory))
        
        return product_template_ids
    
    def get_product_template_by_category_and_partner(self, coefficient_category, partner, category):
        product_template_ids = []
        if coefficient_category.id !=category.id:
            result = self.search([('categ_id','=',category.id), ('partner_id','=',partner.id)])
            if len(result) > 0:
                return product_template_ids
            result = self.search([('categ_id','=',category.id), ('partner_id','=',False)])
            if len(result) > 0:
                return product_template_ids
        
        for ids in self.pool.get("product.template").search([('default_supplier_id','=',partner.id),('categ_id','=',category.id)]):
            product_template_ids.append(ids)
        
        for subCategory in category.child_id:
            product_template_ids.extend(self.get_product_template_by_category_and_partner(coefficient_category, partner, subCategory))
        
        return product_template_ids
    
    @api.one
    @api.onchange('is_brutprice')
    def on_change_is_brutprice(self):
        if self.is_brutprice:
            self.coefficient = 0
    
    @api.one
    @api.constrains('categ_id','partner_id')
    def _check_unique_key(self):
        if not self.categ_id and self.partner_id:
            res = False
        else:
            res = (self.search_count([('categ_id','=',self.categ_id.id),('partner_id','=',self.partner_id.id)]) <= 1)
        if not res:
            raise ValidationError("The coefficient must be unique by partner and category !")
    
    
category_coefficientlist()




'''

To compute sale price there is 2 functions : 
   - get_sale_price give the "catalog" sale price of the product. Optionnaly depending quantity.
   - get_customer_sale_price give the sale price of a product for a customer (depending on his discount)
   
'''   


class product_template(models.Model):
    _inherit = "product.template"
    
    @api.one
    def get_product_product(self):
        res = self.env['product.product'].search([('product_tmpl_id','=',self.id)])
        return res
    
    @api.one
    def get_sale_price(self, quantity=0):
        product_p = self.get_product_product()
        if product_p:
            product_p = product_p[0]
            
        sale_price_computed = 0
        
        if self.compute_sale_price:
            #Get Coefficient List ID
            category = self.categ_id
            category_coefficientlist = False

            while category:
                if product_p.default_supplier_id:
                    result = self.env['elneo_autocompute_saleprice.category_coefficientlist'].search([('categ_id','=',category.id),('partner_id','=',product_p.default_supplier_id.id)])
                    if len(result) > 0:
                        category_coefficientlist = result[0]
                        break
                result = self.env['elneo_autocompute_saleprice.category_coefficientlist'].search([('categ_id','=',category.id),('partner_id','=',False)])
                if len(result) > 0:
                    category_coefficientlist = result[0]
                    break
                category = category.parent_id
                
            if not category_coefficientlist:            
                result = self.env['elneo_autocompute_saleprice.category_coefficientlist'].search([('categ_id','=',False), ('partner_id','=',False)])
                if len(result) > 0:
                    category_coefficientlist = result[0]
            
            #no rules : coeff = 1.3
            if not category_coefficientlist:
                coeff = 1.3
            #rule only for category
            else:
                coeff = category_coefficientlist.coefficient
            
            if category_coefficientlist and category_coefficientlist.is_brutprice:
                if quantity:
                    pricelists = self.default_supplierinfo_id.pricelist_ids.filtered(key=lambda r:r.min_quantity == quantity)
                else:
                    pricelists = self.default_supplierinfo_id.pricelist_ids.sorted(key=lambda r:r.min_quantity)
                if pricelists and pricelists[0].discount != 0:
                    sale_price_computed = pricelists[0].brut_price
            else:
                sale_price_computed = self.cost_price * coeff
                
        self.list_price = max(sale_price_computed, self.sale_price_seller, self.sale_price_fixed)
        return self.list_price
    
    
    
    def get_template_from_partnerinfo(self, cr, uid, ids, context={}):
        return list(set([partnerinfo.suppinfo_id.product_id.id for partnerinfo in self.pool.get("pricelist.partnerinfo").browse(cr, uid, ids, context) if partnerinfo.suppinfo_id and partnerinfo.suppinfo_id.product_id]))
    
    def get_template_from_product(self, cr, uid, ids, context={}):
        result = set()
        for product in self.pool.get("product.product").browse(cr, uid, ids, context):
            try:
                if product and product.product_tmpl_id:
                    result.add(product.product_tmpl_id.id)
            except AttributeError,e:
                pass
        return list(result)
    
    @api.depends('categ_id','cost_price','sale_price_fixed','compute_sale_price','sale_price_seller')
    @api.one
    def _get_list_price(self):
        sale_prices = self.get_sale_price()
        if sale_prices:
            sale_price = sale_prices[0]
        else:
            sale_price = 0
        discount_type = self._context.get("discount_type")
        if discount_type:
            sale_price = self.get_customer_sale_price(discount_type, sale_price)
        self.list_price = sale_price
        return sale_price
        
        
    
    list_price = fields.Float('Sale Price', compute='_get_list_price', help="Base price for computing the customer price. Sometimes called the catalog price.")
    sale_price_fixed = fields.Float('Sale price fixed')
    sale_price_seller = fields.Float('Sale price seller')
    compute_sale_price = fields.Boolean('Autocompute sale price', default=True, help="Sale price is always the highest price, between fixed, seller and cumputed price if checked, between fixed and seller if not checked")
    last_update_price_fixed = fields.Date('Date of last update of fixed price') #this field is updated by a psql trigger
    
    '''    
    store={
    'pricelist.partnerinfo':(get_template_from_partnerinfo, None, 9),  
    'product.product':(get_template_from_product, None, 10),
    'product.template':(lambda self, cr, uid, ids, c={}: ids, None, 10),
    } 
    '''

product_template()

class product_product(models.Model):
    _inherit = "product.product"
    
    def copy(self, cr, uid, ids, default=None, context=None):
        if default is None:
            default = {}
        if context is None:
            context = {}
            
        default.update({'sale_price_fixed':0.0,
                        'compute_sale_price':True})
        
        return super(product_product, self).copy(cr, uid, ids, default, context=context)

product_product()