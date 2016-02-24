from openerp import models, api

class sale_order_line(models.Model):
    _inherit = "sale.order.line"

    @api.model
    def compute_cost_price(self,product, partner, product_cost_price = None):
        price = None
        if product:
            if product_cost_price == None:
                price = product.cost_price
            else:
                price = product_cost_price
            partner_pricelist = partner.property_product_pricelist
    
            if partner_pricelist:
                to_cur = partner_pricelist.currency_id
                frm_cur = self.env.user.company_id.currency_id
                price = frm_cur.compute(price,to_cur, round=False)
        return price
