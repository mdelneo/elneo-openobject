from openerp import models, api

class sale_order(models.Model):
    
    _inherit="sale.order"
    
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        
        if self.partner_id and self.partner_id.property_payment_term.default_order_policy:
            self.order_policy = self.partner_id.property_payment_term.default_order_policy
        
sale_order()