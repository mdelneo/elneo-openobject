# -*- encoding: utf-8 -*-
from openerp import models, api


class sale_order(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def update_prices(self):
        for sale in self:
            for line in sale.order_line:
                line.price_unit = line.product_id.get_customer_sale_price(sale.discount_type_id.id, line.product_id.list_price, line.product_id.cost_price, line.product_uom_qty) 