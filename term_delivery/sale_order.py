from openerp.osv import fields, osv

from openerp import models, api

class sale_order(models.Model):
    
    _inherit="sale.order"
    
    @api.model
    def onchange_partner_id(self,part):
        res = super(sale_order,self).onchange_partner_id(part)
        
        if part :
            partner = self.env['res.partner'].browse(part)
        
            if partner:
                if partner.property_payment_term.default_order_policy:
                    res['value'].update({'order_policy':partner.property_payment_term.default_order_policy})
        
        return res
sale_order()