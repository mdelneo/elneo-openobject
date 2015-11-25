# -*- coding: utf-8 -*-
from openerp import models, api

class sale_order(models.Model):
    
    _inherit='sale.order'

    
    @api.multi
    def onchange_partner_id(self, partner):
        res = super(sale_order, self).onchange_partner_id(partner)
        partner_obj = self.env['res.partner'].browse(partner)
        if not res:
            res = {}
        if 'value' not in res:
            res['value'] = {}
        if partner_obj and partner_obj.property_payment_term.default_order_policy:
            res['value']['order_policy'] = partner_obj.property_payment_term.default_order_policy
        return res
    
         
sale_order()