# -*- coding: utf-8 -*-
from openerp import models,fields,api
from openerp.exceptions import ValidationError

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    def init(self,cr):
        #UPDATE DATABASE TO AVOID NULL PROBLEMS
        query="UPDATE sale_order_line SET name = '.' WHERE name IS NULL"
        
        cr.execute(query)
    
    def compute_stock(self):
        self._qty_virtual_stock()
        self._qty_real_stock()
    
    @api.multi
    @api.onchange('product_id')
    def _qty_virtual_stock(self):
        for sol in self:
            if sol.product_id:
                sol.virtual_stock = sol.product_id.with_context(location=sol.order_id.warehouse_id.lot_stock_id.id).virtual_available
            else:
                sol.virtual_stock = 0 
    
    @api.multi
    @api.onchange('product_id')
    def _qty_real_stock(self):
        for sol in self:
            if sol.product_id:
                sol.real_stock = sol.product_id.with_context(location=sol.order_id.warehouse_id.lot_stock_id.id).qty_available
            else:
                sol.real_stock = 0 
        
    virtual_stock = fields.Float('Virtual stock', compute=_qty_virtual_stock)
    real_stock = fields.Float('Real stock', compute=_qty_real_stock)
    brut_sale_price = fields.Float(related='product_id.product_tmpl_id.list_price', string="Brut sale price", readonly=True)

sale_order_line()   

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    
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
       
    
    partner_order_id = fields.Many2one('res.partner', 'Order Address', readonly=True, required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="Order address for current sales order.")
    quotation_address_id = fields.Many2one('res.partner', 'Quotation Address', readonly=True, required=False, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="Quotation address for current sales order.")
    carrier_id = fields.Many2one('delivery.carrier', 'Delivery Method', help="Complete this field if you plan to invoice the shipping based on picking.")
    is_invoiced = fields.Boolean(compute=_get_is_invoiced, string="Is invoiced", readonly=True,help="Checked if the sale order is completely invoiced",store=True)
    force_is_invoiced = fields.Boolean("Force is invoiced",help="Force the 'invoiced' state for this sale order")
    order_policy = fields.Selection([
                ('manual', 'On Demand'),
                ('picking', 'On Delivery Order'),
                ('prepaid', 'Before Delivery'),
            ],string='Create Invoice', required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
            help="""On demand: A draft invoice can be created from the sales order when needed. \nOn delivery order: A draft invoice can be created from the delivery order when the products have been delivered. \nBefore delivery: A draft invoice is created from the sales order and must be paid before the products can be delivered.""")
    
    purchase_ids = fields.Many2many('purchase.order', 'purchase_invoice_rel', 'invoice_id', 'purchase_id', 'Purchases')
    
    @api.constrains('carrier_id','shop_sale')
    @api.one
    def _check_carrier_id(self):
        if not self.shop_sale and not self.carrier_id:
            raise ValidationError("A delivery method has to be chosen")
    
    @api.depends('purchase_ids')
    def _count_all(self):
        self.purchase_count=len(self.purchase_ids)
    
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
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        
        res = super(sale_order,self).onchange_partner_id(self.partner_id.id)
        
        #TO DELETE WHEN onchange_partner_id WILL BE WITH NEW API
        if res['value'].has_key('fiscal_position'):
            self.fiscal_position = res['value']['fiscal_position']
        if res['value'].has_key('partner_shipping_id'):
            self.partner_shipping_id = res['value']['partner_shipping_id']
        if res['value'].has_key('partner_invoice_id'):
            self.partner_invoice_id = res['value']['partner_invoice_id']
        
        if res['value'].has_key('payment_term'):
            self.payment_term = res['value']['payment_term']
        if res['value'].has_key('user_id'):
            self.user_id = res['value']['user_id']
        if res['value'].has_key('pricelist_id'):
            self.pricelist_id = res['value']['pricelist_id']
        #END TO DELETE WHEN onchange_partner_id WILL BE WITH NEW API
        
        if self.partner_id:
            self.partner_order_id = self.partner_id.address_get(['default'])['default']
            self.sale_note = super(sale_order,self).get_salenote(self.partner_id.id)
            

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

