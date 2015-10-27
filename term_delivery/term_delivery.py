# -*- coding: utf-8 -*-
from openerp import models, fields

class term_delivery(models.Model):
    _inherit='account.payment.term'
    
    default_order_policy = fields.Selection([
            ('prepaid', 'Payment Before Delivery'),
            ('manual', 'Shipping & Manual Invoice'),
            ('picking', 'Invoice From The Picking'),
        ], 'Default Order Policy', required=False, readonly=False)
    
term_delivery()