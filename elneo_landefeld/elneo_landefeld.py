# -*- coding: utf-8 -*-
##############################################################################
#
#    Elneo
#    Copyright (C) 2011-2015 Elneo (Technofluid SA) (<http://www.elneo.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
'''
import base64
import dateutil.parser
import netsvc
import decimal_precision as dp

from ftplib import FTP
from xml.etree.ElementTree import fromstring, ElementTree
from datetime import datetime
from StringIO import *
'''

from openerp import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit='product.template'
    
    @api.multi
    def _is_delivery_cost(self):
        for product in self:
            if self.env['delivery.carrier'].search([('product_id.product_tmpl_id.id','=',product.id)]):
                product.is_delivery_cost = True
            else:
                product.is_delivery_cost = False
    
    is_delivery_cost = fields.Boolean(compute='_is_delivery_cost',string='Is delivery product')
    
    

    @api.multi
    def _calc_seller2(self):
        for product in self.filtered(lambda r:r.seller_ids):
            partner_lists = product.seller_ids.filtered(lambda r:isinstance(r.sequence, (int, long))).sorted(key=lambda r:(r.sequence))
            main_supplier=False
            if self.env.context.get('landefeld_internet_purchase',False):
                
                for supplierinfo in partner_lists:
                    
                    if supplierinfo.name.id == ProductProduct.LANDEFELD_PARTNER_ID:
                        main_supplier = supplierinfo
            else:
                main_supplier = partner_lists and partner_lists[0] or False
                            
            product.seller_delay = main_supplier and main_supplier.delay or 1
            product.seller_qty =  main_supplier and main_supplier.qty or 0.0
            product.seller_id = main_supplier and main_supplier.name.id or False
        return True
    
    seller_delay = fields.Integer(compute=_calc_seller2)
    seller_qty = fields.Float(compute=_calc_seller2)
    seller_id = fields.Many2one(compute=_calc_seller2,comodel_name='res.partner')
    #TODO : A SUPPRIMER ?
    #ref_product_group = fields.Char("Reference Page", size=24, translate=False)
                    
class ProductProduct(models.Model):
    _inherit='product.product'
    
    LANDEFELD_PARTNER_ID = 4509
    LANDEFELD_CATEGORY_ID = 9954
    
    
    @api.model
    def findByCode(self,product_code):
        self.env.cr.execute('select id from product_supplierinfo where sequence = 1 and replace(replace(product_code,\' \',\'\'),\'-\',\'\') ilike %s and name = %s', (product_code.replace(' ','').replace('-',''),self.LANDEFELD_PARTNER_ID))
        supplier_info_ids = [r[0] for r in self.env.cr.fetchall()]
        
        if not supplier_info_ids:
            self.env.cr.execute('select id from product_supplierinfo where replace(replace(product_code,\' \',\'\'),\'-\',\'\') ilike %s and name = %s', (product_code.replace(' ','').replace('-',''),self.LANDEFELD_PARTNER_ID))
            supplier_info_ids = [r[0] for r in self.env.cr.fetchall()]
        
        products=self.env['product.product']
        if supplier_info_ids:
            product_tmpl_ids = list(set([supplier_info.product_tmpl_id.id for supplier_info in self.env['product.supplierinfo'].browse(supplier_info_ids)]))
            products = self.env['product.product'].search([('product_tmpl_id','in',product_tmpl_ids)])
        
        return products
    
    
    def findOrCreateProduct(self,product_code, unit_price, discount_absolute, discount_relative, product_description):
        #Check if product exists
        product_ids = self.findByCode(product_code)

        product_id = None
        if product_ids:
            product_id = product_ids[0]
        
        #Create product if product does not exist
        if not product_id:
            if product_code[0] == '_':
                product_type = 'service'
            else:
                product_type = 'product'
                
            pricelist_values = {
                                                                    'min_quantity' : 1, 
                                                                    'price':unit_price+discount_absolute,
                                                                    'brut_price':unit_price,
                                                                    'discount':discount_relative*100,
                                                                    
                                                                        }
            
            supplierinfo_values={'name':self.LANDEFELD_PARTNER_ID,
                                                               'company_id':1,
                                                               'min_qty':1,
                                                               'delay':0,
                                                               'product_code':product_code,
                                                               'pricelist_ids':[(0,0,pricelist_values)]
                                 
                                 }
            
            product_id = self.env['product.product'].create({
                                                                           'valuation':'manual_periodic',
                                                                           'categ_dpt':1,
                                                                           'categ_family':1,
                                                                           'categ_subfamily':1,
                                                                           'default_code':product_code,
                                                                           #'supply_method': 'buy', 
                                                                           'standard_price':unit_price,
                                                                           'mes_type':'fixed',
                                                                           'uom_id':1,
                                                                           'cost_method':'standard',
                                                                           'name':product_code,
                                                                           'type':product_type,
                                                                           #'procure_method':'make_to_stock',
                                                                           'categ_id':1,  
                                                                           'cost_price':unit_price, 
                                                                           'description_sale':product_description,
                                                                           'seller_ids':[(0,0,supplierinfo_values)]
                                                          })
            
            
            
        return product_id
    
    #TODO: Check if it is used
    #ref_group = fields.Char("Reference Group", size=8, translate=False)
    #ref_page = fields.Char("Reference Page", size=8, translate=False)

    
class PricelistPartnerinfo(models.Model):
    _inherit='pricelist.partnerinfo'
    
    public_price = fields.Float(string='Public price')

class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    @api.model
    def find_by_purchase_order(self, purchase_order_id):
        self.env.cr.execute("""
            SELECT DISTINCT sol.order_id
                FROM sale_order_line sol
                    JOIN sale_order so ON sol.order_id = so.id
                        JOIN procurement_order po ON so.procurement_group_id = po.group_id
                        JOIN purchase_order_line pol ON po.purchase_line_id = pol.id
                        JOIN purchase_order puro ON pol.order_id = puro.id
                WHERE puro.id = %s
            """,[purchase_order_id.id])
        result = self.env.cr.fetchone()
        if result:
            return result[0]
        return False
    
    @api.multi
    def action_button_confirm(self):
        self.ensure_one()
   
        if self.all_landefeld:
            amount = float(self.env['ir.config_parameter'].get_param('elneo_landefeld.landefeld_direct_min_amount',False))
            sale_amount = self._amount_all(None,None)[self.id]['amount_untaxed']
            if amount and (sale_amount > amount):
                return{
                    'name':_("Landefeld order"),
                    'view_mode': 'form',
                    'view_type': 'form',
                    'res_model': 'elneo_landefeld.sale.wizard',
                    'type': 'ir.actions.act_window',
                    'nodestroy': True,
                    'target': 'new',
                    'domain': '[]',
                    'context': dict(self.env.context, active_ids=self._ids)
                }
                
        return super(SaleOrder,self).action_button_confirm()

    landefeld_ref = fields.Char(string = 'Landefeld Reference')
    landefeld_internet_sale = fields.Boolean(string="Landefeld internet sale",index=True)
    landefeld_automatic_sale = fields.Boolean("Landefeld automatic sale") 
    disable_automatic_landefeld = fields.Boolean(string="Disable automatic landefeld")    
    all_landefeld = fields.Boolean(compute='_get_all_landefeld',string="All lines are Landefeld supplied")
    
    @api.multi
    def _get_all_landefeld(self):
        for sale in self:
            #TODO: Check behaviour
            #if self.disable_automatic_landefeld or sale.stop_delivery:
            if sale.disable_automatic_landefeld:
                sale.all_landefeld = False
            else:
                sale.all_landefeld = False
                
                #get all delivery carrier product templates
                for product in sale.order_line.filtered(lambda r:r.product_id and r.product_id.product_tmpl_id).mapped('product_id.product_tmpl_id'):
                    if product.default_supplier_id.id == ProductProduct.LANDEFELD_PARTNER_ID:
                        sale.all_landefeld = True
                    elif not product.is_delivery_cost:
                        sale.all_landefeld=False
                        break
        return True
    
    @api.multi
    def action_ship_create(self):
        #TODO:TO END
        res = super(SaleOrder, self).action_ship_create()
        
        for sale in self:
            for purchase in sale.procurement_group_id.mapped('procurement_ids.purchase_id').filtered(lambda r:r.landefeld_automatic_purchase and r.state != 'cancel'):
                purchase.invoice_method = 'order'
                purchase.signal_workflow('purchase_confirm')
                
                purchase.button_simple_edi_export()
                
        return res
    
    
    @api.one
    def copy(self,default=None):
        if default is None:
            default = {}
        
        default['landefeld_internet_sale'] = False
        default['landefeld_automatic_sale'] = False
        default['disable_automatic_landefeld'] = False
        
        user = self.env.user
        if user.default_warehouse_id:
            default['shop_id'] = user.default_warehouse_id
        
        return super(SaleOrder,self).copy(default=default)
        
         
class StockRoute(models.Model):
    _inherit='stock.location.route'
    
    landefeld_dropship = fields.Boolean(string='Landefeld Dropship',help='If this is checked, when a sale order is forced to be send from Landefeld to customer directly, use this route.')
    
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    landefeld_ref = fields.Text('Landefeld Ref', size=255)
    landefeld_customer_ref = fields.Text('Landefeld customer ref', size=255)
    landefeld_internet_purchase = fields.Boolean("Landefeld internet purchase") 
    landefeld_automatic_purchase = fields.Boolean("Landefeld automatic purchase") 
    landefeld_orderresponse_received = fields.Boolean("Landefeld order response received")
    landefeld_dispatchnote_received = fields.Boolean("Landefeld dispatch note received")
    landefeld_orderresponse_alert_sent = fields.Boolean("Landefeld order response alert sent")
    landefeld_dispatchnote_alert_sent = fields.Boolean("Landefeld dispatch note alert sent")
    
    @api.one
    def copy(self,default=None):
        if default is None:
            default = {}
       
        default['landefeld_internet_purchase'] = False
        default['landefeld_automatic_purchase'] = False
        default['landefeld_ref'] = ''
        
        return super(PurchaseOrder, self).copy(default)
    
    
class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    landefeld_ref = fields.Char(string="Landefeld Ref", size=64)


class StockMove(models.Model):
    _inherit = 'stock.move'
    
    landefeld_internet_sale = fields.Boolean(related='picking_id.sale_id.landefeld_internet_sale',string="Landefeld internet sale")
    landefeld_automatic_sale = fields.Boolean(related='picking_id.sale_id.landefeld_automatic_sale',string="Landefeld automatic sale")
    

class ProcurementOrder(models.Model):
    _inherit = 'procurement.order'
    
    @api.multi
    def make_po(self):
        res={}
        for procurement in self:
            if procurement.sale_line_id and procurement.sale_line_id.order_id and procurement.sale_line_id.order_id.landefeld_internet_sale:
                result = super(ProcurementOrder,procurement.with_context(landefeld_internet_purchase=True)).make_po()
            else:
                result = super(ProcurementOrder,procurement).make_po()
            #set internet sale in context to force landefeld selection for default supplier in _calc_supplier method (product.template) 
            
            res.update(result)
         
        
        purchase_ok = []
        #set purchase as automatic or internet if it's necessary
        for proc, purchase_line in res.iteritems():
            purchase = self.env['purchase.order.line'].browse([purchase_line]).order_id
            if purchase not in purchase_ok:
                procurement = self.env['procurement.order'].browse(proc)
                if procurement.sale_line_id and procurement.sale_line_id.order_id:
                    if procurement.sale_line_id.order_id.landefeld_automatic_sale:
                        purchase.landefeld_automatic_purchase = True
                        purchase_ok.append(purchase)
                    if procurement.sale_line_id.order_id.landefeld_internet_sale:
                        purchase.landefeld_internet_purchase = True
                        purchase_ok.append(purchase)
            
        return res
    
class PurchaseOrderLine(models.Model): 
    _inherit = "purchase.order.line"
    
    def findPurchaseLineByProduct(self,purchase_order, products):
        '''
        @params:    purchase_order: purchase.order
                    products : product.product
        '''
        for line in purchase_order.order_line:
            if line.product_id in products:
                return line
        return None

       
'''
class sale_order(osv.osv): 
    _inherit = "sale.order"
    
    
    def find_by_purchase_order(self, cr, uid, purchase_order_id, context):
        cr.execute("""
            select distinct sale_order_line.order_id 
            from sale_order_line 
                left join stock_move
                    left join procurement_order on procurement_order.move_id = stock_move.id
                on sale_line_id = sale_order_line.id
            where procurement_order.purchase_id = %s
            """,(purchase_order_id,))
        result = cr.fetchone()
        if result:
            return result[0]
        return False
    

class purchase_order_line(osv.osv): 
    _inherit = "purchase.order.line"
    
    def findPurchaseLineByProduct(self, cr, uid, purchase_order, product_ids):
        for line in purchase_order.order_line:
            if line.product_id.id in product_ids:
                return line.id
        return None
purchase_order_line()

class purchase_order(osv.osv): 
    _inherit = "purchase.order"
   
    #used by workflow to bypass picking creation
    def is_landefeld_order(self,cr, uid, ids, *args):
        for order in self.browse(cr, uid, ids):
            if order.landefeld_internet_purchase or order.landefeld_automatic_purchase:
                return True
        return False
    
    def find_by_sale_order(self, cr, uid, sale_order_id, context):
        cr.execute("""
            select distinct purchase_id 
            from procurement_order                
            left join stock_move
                left join sale_order_line
                on stock_move.sale_line_id = sale_order_line.id
            on procurement_order.move_id = stock_move.id
            where sale_order_line.order_id = %s                
            """,(sale_order_id,))
        result = cr.fetchone()
        return result and result[0] or False
     
     
     
    def send_by_open_trans(self, cr, uid, ids, context=None):
        export_landefeld_pool = self.pool.get("elneo_landefeld.exports_landefeld")
        export_landefeld_pool.export_xml_order(cr, uid, ids, context)
        return True
     
purchase_order()


'''