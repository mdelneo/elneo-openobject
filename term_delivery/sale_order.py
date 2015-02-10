# -*- coding: utf-8 -*-
from openerp import models, api

class sale_order(models.Model):
    
    _inherit='sale.order'

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        
        # BEGIN - TO SUPPRESS - WHEN SALE.ORDER SUPPORTS NEW API 
        if not self.partner_id:
            self.partner_invoice_id = False
            self.partner_shipping_id = False
            self.payment_term = False
            self.fiscal_position = False
        else:
            addr = self.partner_id.address_get(['delivery', 'invoice', 'contact'])
            self.partner_shipping_id = addr['delivery']
            self.partner_invoice_id = addr['invoice']
            self.payment_term = self.partner_id.property_payment_term.id
            self.user_id = self.partner_id.user_id.id or self.env.uid
            if self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id:
                self.pricelist_id = self.partner_id.property_product_pricelist.id
            self.sale_note = self.get_salenote(self.partner_id.id)
         # END - TO SUPPRESS  
         
            if self.partner_id and self.partner_id.property_payment_term.default_order_policy:
                self.order_policy = self.partner_id.property_payment_term.default_order_policy
    
         
sale_order()