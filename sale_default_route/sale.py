# -*- coding: utf-8 -*-
from openerp import models, api

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    
    @api.multi
    def product_id_change_with_wh(self, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, warehouse_id=False):
        
        res = super(sale_order_line, self).product_id_change_with_wh(pricelist, product, qty=qty,
            uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, warehouse_id=warehouse_id)
        
        if not res:
            res = {}
        if not 'value' in res:
            res['value'] = {}
            
        route_id = int(self.env['ir.config_parameter'].get_param('sale_default_route.default_route',False))
        res['value']['route_id'] = route_id
        
        return res
          
sale_order_line()

