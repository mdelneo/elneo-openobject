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
                line.discount = wiz.discount