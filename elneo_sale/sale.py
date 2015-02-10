# -*- coding: utf-8 -*-
from openerp import models,fields,api

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    partner_order_id = fields.Many2one('res.partner', 'Order Address', readonly=True, required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="Order address for current sales order.")
    quotation_address_id = fields.Many2one('res.partner', 'Quotation Address', readonly=True, required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="Quotation address for current sales order.")
    
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
                
    
sale_order()