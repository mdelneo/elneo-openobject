from openerp import models,fields,api
from openerp.tools.float_utils import float_compare, float_round


class sale_order_line(models.Model):
    _inherit = "sale.order.line"
    
    #set the cost price in sale order line when product change
    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, shop_id=0, context={}):
        
        res = super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty=qty,
            uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, context=context)
        
        if product:
            product_obj = self.pool.get('product.product').browse(cr, uid, product)
            
            #get cost price for quantity
            suppinfo = product_obj.seller_ids and product_obj.seller_ids[0]
            
            price = 0
            if suppinfo:
                pricelist = suppinfo.name and suppinfo.name.cost_price_product_pricelist and suppinfo.name.cost_price_product_pricelist.id
                
                supplier_id = context.get("supplier_id",None)
                
                if pricelist:
                    price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
                        product, qty, supplier_id)[pricelist]
                        
            if not price:
                price = product_obj.cost_price
            
            partner_pricelist = self.pool.get('res.partner').browse(cr, uid, partner_id).property_product_pricelist

            if partner_pricelist:
                to_cur = partner_pricelist.currency_id.id
                frm_cur = self.pool.get('res.users').browse(cr, uid, uid).company_id.currency_id.id
                price = self.pool.get('res.currency').compute(cr, uid, frm_cur, to_cur, price, round=False)

            res['value'].update({'purchase_price': price})
            
            #Add a warning if cost_price = 0
            if not res['value']['purchase_price']:
                res['warning'] = {'title': 'No cost price', 'message':'Product %s has a zero cost price'%product_obj.default_code}
            
        return res
    
    #just replace Standard price to purchase_price in sale_order_line margin computation
    def _product_margin(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = 0
            if line.product_id:
                res[line.id] = round((line.price_unit*line.product_uom_qty*(100.0-line.discount)/100.0) -(line.purchase_price*line.product_uom_qty), 2)
        return res


class res_partner(models.Model):
    _inherit = 'res.partner'
    
    cost_price_product_pricelist = fields.Many2one('product.pricelist', string='Cost Pricelist', company_dependent=True, help="This pricelist is used to set the cost price of a product based on the pricelist of the prefered supplier for this product")
    

class product_template(models.Model):
    _inherit = "product.template"
    
    cost_price = fields.Float('Cost price', compute='_get_cost_price', method=True, store=True)
    cost_price_fixed = fields.Float(string='Cost price fixed', help="It's based on the purchase price (with the shipping cost")
    compute_cost_price = fields.Boolean(string='Autocompute cost price', help="When checked, cost price is computed", default=True)
    
    ''' REPLACED BY api.depends
    def onchange_seller_ids(self, cr, uid, ids, compute_cost_price = True, cost_price_fixed = 0):
        if len(ids) == 1:
            cost_price = self._get_cost_price(cr, uid, ids, args={'compute_cost_price':compute_cost_price, 'cost_price_fixed':cost_price_fixed})[ids[0]]
            return {'value': {'cost_price':cost_price}}
        return {}
    
    def onchange_compute_cost_price(self, cr, uid, ids, compute_cost_price = True, cost_price_fixed = 0):
        if len(ids) == 1:
            return {'value': {'cost_price':self._get_cost_price(cr, uid, ids, args={'compute_cost_price':compute_cost_price, 'cost_price_fixed':cost_price_fixed})[ids[0]]}}
        return {}
    '''    
    
    
    @api.depends('compute_cost_price','cost_price_fixed','seller_ids.pricelist_ids.price')
    def _get_cost_price(self):
        for product in self:
            
            if not product.compute_cost_price:
                product.cost_price = product.cost_price_fixed
            else:
                supplierinfos = product.seller_ids
            
                if len(supplierinfos) > 0:
                    supplierinfo = supplierinfos[0]
                    
                    pricelist = supplierinfo.name.cost_price_product_pricelist.id
                    if pricelist and not (type(product.id) is models.NewId):
                        price = self.pool.get('product.pricelist').price_get(self._cr, self._uid, [pricelist],
                                product.id, 1.0)[pricelist]
                        product.cost_price = price
                    else:
                        product.cost_price = 0                    
            
        return product.cost_price
    
    def compute_all_costprice(self,cr,uid,ids,context=None):
        cr.execute("select id from product_product order by id")
        product_ids = cr.fetchall()
        product_ids = [product_id[0] for product_id in product_ids]
        self.write(cr, uid, product_ids, {})
    
    def _get_sale_price(self, cr, uid,ids,name = None,args=None, context=None):
        res = {}
       
        if len(ids)>1:
            return res
        for product in self.browse(cr, uid, ids, context=context):
            pricelist = self.pool.get('product.pricelist').search(cr,uid,[('id','=', 1)])[0]
            price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
                            product.id, 1.0)[pricelist]
            res[product.id] = price
           
        return res
    
    def _cost_price_search_partnerinfo(self, cr, uid, ids, context=None):
        """ Finds operations for a production order.
        @return: List of ids
        """
        partnerinfo = self.pool.get('pricelist.partnerinfo').browse(cr, uid,ids[0], context=context)
        product_id = partnerinfo.suppinfo_id.product_id.id
        product_ids = self.pool.get('product.product').search(cr, uid, [('product_tmpl_id','=',product_id)], context=context)
        return product_ids    
    
    def get_product_from_partnerinfo(self, cr, uid, ids, context={}):
        product_templates = list(set([partnerinfo.suppinfo_id.product_id.id for partnerinfo in self.pool.get("pricelist.partnerinfo").browse(cr, uid, ids, context) if partnerinfo.suppinfo_id and partnerinfo.suppinfo_id.product_id]))
        return self.pool.get("product.product").search(cr, uid, [('product_tmpl_id','in',product_templates)], context=context)
    
