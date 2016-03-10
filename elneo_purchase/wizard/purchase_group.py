from openerp import models, fields, api

class PurchaseOrderGroup(models.TransientModel):
    _inherit = "purchase.order.group"
    
    def _get_payment_term(self):
        res=self.env['account.payment.term']
        active_ids = self.env.context.get('active_ids',False)
        
        if active_ids:
            purchase = self.env['purchase.order'].browse(active_ids[0])
            
            if purchase.partner_id.property_supplier_payment_term:
                res = purchase.partner_id.property_supplier_payment_term.id
            elif purchase.payment_term:
                res = purchase.payment_term.id
        
        return res
    
    payment_term = fields.Many2one('account.payment.term',string='Payment Term',default=_get_payment_term)
           
    @api.multi
    def merge_orders(self):
        res = super(PurchaseOrderGroup,self.with_context(payment_term_id=self.payment_term.id)).merge_orders()
        
        return res
    
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    @api.multi
    def do_merge(self):
        res = super(PurchaseOrder,self).do_merge()
        
        payment_term_id = self.env.context.get('payment_term_id',False)
        if payment_term_id:
            payment_term = self.env['account.payment.term'].browse(payment_term_id)
            for key in res.keys():
                new_purchase = self.env['purchase.order'].browse(key)
                new_purchase.payment_term_id = payment_term
           
            
        return res
        