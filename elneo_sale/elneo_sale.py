# -*- coding: utf-8 -*-
import logging
from openerp import models,fields,api
from openerp.exceptions import ValidationError
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

class procurement_order(models.Model):
    _inherit = 'procurement.order'
    
    @api.multi
    def make_po(self):
        #to force new purchase order creation, when we call "make po", say to search function of purchase order that it does not exists other purchase order
        #to do it we pass make_po = True to the context
        self = self.with_context(make_po=True)
        res = super(procurement_order, self).make_po()
        return res
    

class purchase_order(models.Model):
    _inherit = 'purchase.order'
    
    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        #if make_po = True, we simulate that no other purchase order exists, to force new purchase order creation
        if self._context.get('make_po',False):
            return self
        return super(purchase_order, self).search(args, offset=offset, limit=limit, order=order, count=count)
    
class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    def init(self,cr):
        #UPDATE DATABASE TO AVOID NULL PROBLEMS
        query="""UPDATE sale_order_line SET name = '.' WHERE name IS NULL"""
        cr.execute(query)
    
    def compute_stock(self):
        self._qty_virtual_stock()
        self._qty_real_stock()
    
    def _qty_virtual_stock(self):
        for sol in self:
            if sol.product_id:
                sol.virtual_stock = sol.product_id.with_context(location=sol.order_id.warehouse_id.lot_stock_id.id).virtual_available
            else:
                sol.virtual_stock = 0 
    
    def _qty_real_stock(self):
        for sol in self:
            if sol.product_id:
                sol.real_stock = sol.product_id.with_context(location=sol.order_id.warehouse_id.lot_stock_id.id).qty_available
            else:
                sol.real_stock = 0
                
    @api.multi
    def copy(self, default=None):
        if not default:
            default = {}
        default['purchase_line_ids'] = None
        return super(sale_order_line, self).copy(default) 


    @api.multi
    def product_id_change_with_wh(self, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, warehouse_id=False):
        
        res = super(sale_order_line, self).product_id_change_with_wh(pricelist, product, qty=qty,
            uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, warehouse_id=warehouse_id)
        
        if res and res.get('warning',False) and res['warning'].get('title',False) and res['warning']['title'] == _('Configuration Error!'):
            del res['warning'] 
            
        
        old_price = self._context.get('price_unit',0)
        new_price = res.get('value',{'price_unit':0}).get('price_unit',0)
        
        if old_price and old_price != new_price:
            res['warning'] = {'title':'Unit price changed','message':_('Unit price has been changed from %s to %s.')%(old_price,new_price)}
        
        #compute qty real/virtual stock    
        product_obj = self.env['product.product'].browse(product)
        warehouse = self.env['stock.warehouse'].browse(warehouse_id)
        if not res:
            res = {}
        if not 'value' in res:
            res['value'] = {}
        
        res['value']['virtual_stock'] = product_obj.with_context(location=warehouse.lot_stock_id.id).virtual_available
        res['value']['real_stock'] = product_obj.with_context(location=warehouse.lot_stock_id.id).qty_available
        
        return res
        
        
    virtual_stock = fields.Float('Virtual stock', compute=_qty_virtual_stock)
    real_stock = fields.Float('Real stock', compute=_qty_real_stock)
    brut_sale_price = fields.Float(related='product_id.product_tmpl_id.list_price', string="Brut sale price", readonly=True)

    purchase_line_ids = fields.Many2many('purchase.order.line', 'purchase_line_sale_line_rel', 'sale_line_id', 'purchase_line_id', 'Purchase lines')

sale_order_line()   

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    @api.multi
    def onchange_pricelist_id(self, pricelist_id, order_lines):
        res = super(sale_order, self).onchange_pricelist_id(pricelist_id, order_lines)
        if res and 'warning' in res:
            del res['warning']
        return res
    
    @api.multi
    def copy(self, default=None):
        if not default:
            default = {}
        default['purchase_ids'] = None
        return super(sale_order, self).copy(default)
    
    @api.one
    @api.depends('invoice_ids.state','force_is_invoiced')
    def _get_is_invoiced(self):
        result = {}  
        
        self.is_invoiced = False
        
        # if is force_is_invoice
        if self.force_is_invoiced:
            self.is_invoiced = True
            
        # Maintenance Order
        # V8 : TO PUT IN A SEPARATE MODULE#
        #if order.intervention_id and (len(order.invoice_ids) > 0):
        #    is_invoiced = True
    
        
        if not self.is_invoiced:
            has_invoice_line = False
            has_order_line = False
            all_order_line_is_invoiced = True
            for order_line in self.order_line:
                if order_line.state == 'cancel':
                    continue
                
                has_order_line = True
                quantityInInvoiceLine = 0
                for invoice_line in order_line.invoice_lines:
                    if invoice_line.invoice_id.state != "draft" and invoice_line.invoice_id.state != "cancel" and invoice_line.invoice_id.type == "out_invoice":
                        has_invoice_line = True
                        quantityInInvoiceLine += invoice_line.quantity
                if quantityInInvoiceLine != order_line.product_uom_qty:
                    all_order_line_is_invoiced = False
                    break
            self.is_invoiced = all_order_line_is_invoiced and has_invoice_line and has_order_line

        # if linked invoice
        if not self.is_invoiced:
            invoiceAmounts = {}
            saleAmounts = {}
            for invoice in self.invoice_ids:
                if invoice.state != "draft" and invoice.state != "cancel" and invoice.type == "out_invoice":
                    if not invoice.id in invoiceAmounts:
                        invoiceAmounts[invoice.id] = invoice.amount_total
                        for sale in invoice.sale_order_ids:
                            if not sale.id in saleAmounts:
                                saleAmounts[sale.id] = sale.amount_total
                           
            sumInvoice = 0
            sumSale = 0
            for key in invoiceAmounts.keys():
                sumInvoice += invoiceAmounts[key]
                
            for key in saleAmounts.keys():
                sumSale += saleAmounts[key]

            if (sumInvoice != 0 or sumSale != 0) and sumInvoice >= sumSale:
                self.is_invoiced = True
       
    
    partner_order_id = fields.Many2one('res.partner', 'Order Address', readonly=True, required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},default=lambda rec: rec.partner_id, help="Order address for current sales order.")
    carrier_id = fields.Many2one('delivery.carrier', 'Delivery Method', help="Complete this field if you plan to invoice the shipping based on picking.")
    is_invoiced = fields.Boolean(compute=_get_is_invoiced, string="Is invoiced", readonly=True,help="Checked if the sale order is completely invoiced",store=True)
    force_is_invoiced = fields.Boolean("Force is invoiced",help="Force the 'invoiced' state for this sale order")
    order_policy = fields.Selection([
                ('manual', 'On Demand'),
                ('picking', 'On Delivery Order'),
                ('prepaid', 'Before Delivery'),
            ],string='Create Invoice', required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
            help="""On demand: A draft invoice can be created from the sales order when needed. \nOn delivery order: A draft invoice can be created from the delivery order when the products have been delivered. \nBefore delivery: A draft invoice is created from the sales order and must be paid before the products can be delivered.""")
    
    purchase_ids = fields.Many2many('purchase.order', 'purchase_sale_rel', 'sale_id', 'purchase_id', 'Purchases')
    
    @api.constrains('carrier_id','shop_sale')
    @api.one
    def _check_carrier_id(self):
        from_opportunity = False
        if self._context and self._context.get('active_model',False) and self._context['active_model'] == 'crm.lead':
            from_opportunity = True
        if not self.shop_sale and not self.carrier_id and not from_opportunity:
            raise ValidationError("A delivery method has to be chosen")
    
    @api.depends('purchase_ids')
    @api.multi
    def _count_all(self):
        for sale in self:
            sale.purchase_count=len(sale.purchase_ids)
    
    purchase_count = fields.Integer(compute=_count_all, method=True)
    
    @api.multi
    def view_purchase(self):
        '''
        This function returns an action that display existing purchase orders of given purchase order ids.
        It load the tree or the form according to the number of purchase orders
        '''
        
        mod_obj = self.env['ir.model.data']
        dummy, action_id = tuple(mod_obj.get_object_reference('purchase', 'purchase_form_action'))
        action_obj = self.env['ir.actions.act_window'].browse(action_id)
        action = action_obj.read()[0]
        

        #override the context to get rid of the default filtering on picking type
        action['context'] = {}
        #choose the view_mode accordingly
        if self.purchase_count > 1:
            action['domain'] = "[('id','in',[" + ','.join(map(str, self.purchase_order.mapped('id'))) + "])]"
        else:
            res = mod_obj.get_object_reference('purchase', 'view_order_form')
            action['views'] = [(res and res[1] or False, 'form')]
            action['res_id'] = self.purchase_orders.mapped('id')[0] or False
        return action
    
    #function to rewrite when odoo core will be migrated to new api
    def onchange_warehouse_id(self, cr, uid, ids, warehouse_id, context=None):
        res = super(sale_order, self).onchange_warehouse_id(cr, uid, ids, warehouse_id, context)
        self.browse(cr, uid, ids, context).order_line.compute_stock()
        return res
    
    @api.onchange('order_line')
    def onchange_order_lines(self):
        self.order_line.compute_stock()
        
    @api.multi
    def onchange_partner_id(self, partner):
        res = super(sale_order, self).onchange_partner_id(partner)
        if partner:
            partner_obj = self.env['res.partner'].browse(partner)
            if not res:
                res = {}
            if not 'value' in res:
                res['value'] = {}
            res['value']['partner_order_id'] = partner_obj.address_get(['default'])['default']
            res['value']['sale_note'] = super(sale_order,self).get_salenote(partner)
        return res

    @api.onchange('partner_order_id')
    def onchange_partner_order_id(self):
        if not self.partner_order_id:
            self.partner_id = False
            self.partner_invoice_id = False
            self.partner_shipping_id = False
            self.quotation_address_id = False
            self.payment_term = False
            self.fiscal_position = False
        else:
            # GET the commercial entity
            if self.partner_order_id.commercial_partner_id:
                self.partner_id = self.partner_order_id.commercial_partner_id
                addr = self.partner_id.address_get(['delivery', 'invoice', 'contact'])
                self.partner_shipping_id = addr['delivery']
                self.partner_invoice_id = addr['invoice']
                
    @api.onchange('quotation_address_id')
    def onchange_quotation_address_id(self):
        
        if not self.quotation_address_id:
            self.partner_id = False
            self.partner_invoice_id = False
            self.partner_shipping_id = False
            self.partner_order_id = False
            self.payment_term = False
            self.fiscal_position = False
        else:
            # GET the commercial entity
            if self.quotation_address_id.commercial_partner_id:
                self.partner_id = self.quotation_address_id.commercial_partner_id
                addr = self.partner_id.address_get(['delivery', 'invoice', 'contact'])
                self.partner_shipping_id = addr['delivery']
                self.partner_invoice_id = addr['invoice']


class pricelist_partnerinfo(models.Model):
    _inherit = 'pricelist.partnerinfo'
    
    brut_price = fields.Float('Brut price')
    discount = fields.Float('Discount')



class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    sale_order_ids =fields.Many2many('sale.order', 'sale_order_invoice_rel', 'invoice_id', 'order_id', string='Sale orders')

