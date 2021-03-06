from openerp import models,fields,api,_
from openerp.tools.float_utils import float_compare, float_round
from datetime import datetime
from openerp.exceptions import Warning


class sale_global_discount_wizard(models.TransientModel):
    _inherit = 'sale.global.discount.wizard'
    
    @api.multi
    def process(self):
        res = super(sale_global_discount_wizard, self).process()
        sale = self.env['sale.order'].browse(self._context.get('active_id'))
        sale._get_margin_elneo()
        sale._get_margin_elneo_coeff()
        return res
        
class purchase_order_line(models.Model):
    _inherit = 'purchase.order.line'
    
    def _get_sale_order_lines(self):
        sale_lines = []
        for move in self.move_ids:
            current_stock_move = move
            while current_stock_move:
                if current_stock_move.procurement_id.sale_line_id:
                    sale_lines.append(current_stock_move.procurement_id.sale_line_id)
                current_stock_move = current_stock_move.move_dest_id
        return sale_lines
    
    @api.multi
    def write(self, vals):
        #update cost price of related sale orders when price change in a purchase order line
        res = super(purchase_order_line, self).write(vals)
        if 'price_unit' in vals:
            sale_order_lines = self._get_sale_order_lines()
            if sale_order_lines:
                supplier_id = vals.get('partner_id',False)
                if not supplier_id:
                    supplier = self.partner_id
                else:
                    supplier = self.env['res.partner'].browse(supplier_id)
                supplier = supplier.commercial_partner_id
                
                product_id = vals.get('product_id',self.product_id.id)
                qty = vals.get('product_qty',self.product_qty)
                cost_pricelist = supplier.cost_price_product_pricelist                   
                cost_price = cost_pricelist.price_get(product_id, qty, supplier.id)[cost_pricelist.id]
                for line in sale_order_lines:
                    line.purchase_price = cost_price
        return res
        

class sale_order_line(models.Model):
    _inherit = "sale.order.line"
    
    #set the cost price in sale order line when product change
    @api.multi
    def product_id_change(self, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False):
        
        res = super(sale_order_line, self).product_id_change(pricelist, product, qty=qty,
            uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag)
        
        if product:
            product_obj = self.env['product.product'].browse(product)
            
            #get cost price for quantity
            suppinfo = product_obj.seller_ids and product_obj.seller_ids[0]
            
            
            if product_obj.distinct_price_by_qty:
                price = 0
                if suppinfo:
                    pricelist = suppinfo.name and suppinfo.name.cost_price_product_pricelist and suppinfo.name.cost_price_product_pricelist.id
                    
                    supplier_id = self._context.get("supplier_id",None)
                    
                    if pricelist:
                        price = self.env['product.pricelist'].browse(pricelist).price_get(product, qty, supplier_id)[pricelist]
            else:
                price = product_obj.cost_price
            
            partner_pricelist = self.env['res.partner'].browse(partner_id).property_product_pricelist

            if partner_pricelist:
                to_cur = partner_pricelist.currency_id
                frm_cur = self.env['res.users'].browse(self._uid).company_id.currency_id
                if to_cur != frm_cur:
                    price = frm_cur.compute(price, to_cur, round=False)

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
                res[line.id] = round(line.price_unit*line.product_uom_qty -(line.purchase_price*line.product_uom_qty), 2)
        return res
    
    @api.one
    @api.depends('price_unit','product_uom_qty','purchase_price')
    def _get_margin_elneo(self):
        self.margin_elneo = round(self.price_unit*self.product_uom_qty -(self.purchase_price*self.product_uom_qty), 2)
    
    margin_elneo = fields.Float('Margin', compute='_get_margin_elneo', store=True)
    
    
class sale_order(models.Model):
    _inherit = 'sale.order'
    
    @api.one
    @api.onchange('order_line')
    @api.depends('order_line')
    def _get_margin_elneo(self):
        margin = 0
        for line in self.order_line:
            margin = margin + line.margin_elneo
        self.margin_elneo = margin
        
        
    @api.one
    @api.onchange('order_line')
    @api.depends('order_line')
    def _get_margin_elneo_coeff(self):
        sale_price = 0
        cost_price = 0
        for line in self.order_line:
            sale_price = sale_price + line.price_unit*line.product_uom_qty
            cost_price = cost_price + line.purchase_price*line.product_uom_qty
        if cost_price:
            self.margin_elneo_coeff = sale_price / cost_price
        else:
            self.margin_elneo_coeff = 0
        
    
    margin_elneo = fields.Float('Margin', compute='_get_margin_elneo', store=True)
    margin_elneo_coeff = fields.Float('Margin (Coeff)', compute='_get_margin_elneo_coeff', store=True)


class res_partner(models.Model):
    _inherit = 'res.partner'
    
    cost_price_product_pricelist = fields.Many2one('product.pricelist', string='Cost Pricelist', company_dependent=True, help="This pricelist is used to set the cost price of a product based on the pricelist of the prefered supplier for this product")
    
class product_product(models.Model):
    _inherit='product.product'
    
    @api.multi
    def on_change_compute_cost_price(self, compute_cost_price, cost_price_fixed):
        return self.product_tmpl_id.on_change_compute_cost_price(compute_cost_price,cost_price_fixed)
    

class product_template(models.Model):
    _inherit = "product.template"
    
    @api.multi
    def _get_distinct_by_qty(self):
        self._cr.execute('''select pt.id, avg(pp.min_quantity) != min(pp.min_quantity) from 
            pricelist_partnerinfo pp 
            left join product_supplierinfo ps 
                left join product_template pt on ps.product_tmpl_id = pt.id
            on ps.id = pp.suppinfo_id
            where pt.default_supplier_id = ps.name and product_tmpl_id in %s
            group by pt.id;''', (tuple([p.id for p in self]),))
        results = self._cr.fetchall()
        for res in results:
            for product in self:
                if product.id == res[0]:
                    product.distinct_price_by_qty = res[1]
             
        
    
    cost_price = fields.Float('Cost price', compute='_get_cost_price', method=True, store=True)
    cost_price_fixed = fields.Float(string='Cost price fixed', help="It's based on the purchase price (with the shipping cost")
    compute_cost_price = fields.Boolean(string='Autocompute cost price', help="When checked, cost price is computed", default=True)
    distinct_price_by_qty = fields.Boolean(string='Distinct price by quantity', compute='_get_distinct_by_qty', help='Checked if product has different purchase prices depending on quantity for default supplier')
    
    
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

    @api.multi
    def on_change_compute_cost_price(self, compute_cost_price, cost_price_fixed):
        context_onchange = {'compute_cost_price':compute_cost_price,'cost_price_fixed':cost_price_fixed,'product_tmpl_id':self.id}
        new_cost_price = self.with_context(onchange=context_onchange)._get_cost_price()
        if type(new_cost_price) is list:
            if len(new_cost_price) > 0:
                new_cost_price = new_cost_price[0]
            else:
                new_cost_price = 0.
        return {'value':{'cost_price':new_cost_price}}
    
    @api.one
    @api.depends('compute_cost_price','cost_price_fixed','seller_ids.pricelist_ids.price')
    def _get_cost_price(self):
        
        cost_price = 0.0
        
        #get values from old api
        if 'onchange' in self._context:
            cost_price_fixed = self._context['onchange']['cost_price_fixed']
            compute_cost_price = self._context['onchange']['compute_cost_price']
            product_tmpl_id = self._context['onchange']['product_tmpl_id']
        else:
            cost_price_fixed = self.cost_price_fixed
            compute_cost_price = self.compute_cost_price
            product_tmpl_id = self.id
            
        if not compute_cost_price:
            cost_price = cost_price_fixed
        else:
            supplierinfos = self.seller_ids
        
            if len(supplierinfos) > 0:
                supplierinfo = supplierinfos[0]
                
                pricelist = supplierinfo.name.cost_price_product_pricelist
                
                #find product template id
                if not product_tmpl_id:
                    if not (type(self.id) is models.NewId):
                        product_tmpl_id = self.id
                    elif self._context and 'params' in self._context and 'id' in self._context['params']:
                        product_tmpl_id = self._context['params']['id']
                        
                if pricelist and product_tmpl_id:
                    #bypass price_get method in pricelist cause this function require a product_product and sub-functions not. So call directly sub-functions.
                    product_tmpl = self.env['product.template'].browse(product_tmpl_id)
                    res_multi = pricelist.price_rule_get_multi(products_by_qty_by_partner=[(product_tmpl, product_tmpl.uom_id.id, None)])
                    if res_multi and (product_tmpl.id in res_multi) and (pricelist.id in res_multi[product_tmpl.id]) and len(res_multi[product_tmpl.id][pricelist.id]) > 0:
                        cost_price = res_multi[product_tmpl.id][pricelist.id][0]
                    else:
                        cost_price = 0
                        
        self.cost_price = cost_price
        return cost_price                    
            
    
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
    
