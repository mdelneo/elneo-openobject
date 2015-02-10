from openerp import models,fields,api

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    partner_order_id = fields.Many2one('res.partner', 'Order Address', readonly=True, required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="Order address for current sales order.")
    quotation_address_id = fields.Many2one('res.partner', 'Quotation Address', readonly=True, required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="Quotation address for current sales order.")
    
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
            self.sale_note = super(sale_order,self).get_salenote(self.partner_id.id)
        # END - TO SUPPRESS    
            

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