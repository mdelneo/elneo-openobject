from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
from openerp import models,fields,api
from operator import itemgetter
import re

class sale_global_discount_wizard(models.TransientModel):
    _name = 'sale.global.discount.wizard'
    
    discount = fields.Float('Discount')
    
    @api.multi
    def process(self):
        sale_order = self.env['sale.order'].browse(self._context.get('active_id'))
        for wiz in self:
            for line in sale_order.order_line:
                if line.product_id.type == 'service':
                    continue
                old_discount = line.discount
                old_brut_price = line.price_unit
                old_net_price = old_brut_price - (old_discount/100.)*old_brut_price
                additionnal_discount = wiz.discount
                new_net_price = old_net_price - (additionnal_discount/100.)*old_net_price
                if old_brut_price:
                    new_discount = 100. - (100. * new_net_price / old_brut_price)
                else:
                    new_discount = old_discount
                line.discount = new_discount
                line.price_unit = line.brut_sale_price - (line.brut_sale_price*line.discount/100)