# -*- coding: utf-8 -*-
from openerp import models, api, fields

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    def _default_route(self):
        route_id = self.env['ir.config_parameter'].get_param('sale_default_route.default_route',False)
        if not (type(route_id) is int):
            try:
                route_id = int(route_id)
            except Exception,e:
                route_id = None
        return route_id
    
    @api.model
    def default_get(self, fields_list):
        res = super(sale_order_line,self).default_get(fields_list)
        if 'route_id' in fields_list:
            res['route_id'] = self._default_route()
        return res
    
    @api.multi
    def product_id_change(self, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False):
        
        res = super(sale_order_line, self).product_id_change(pricelist, product, qty=qty,
            uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag)
        
        if not res:
            res = {}
        if not 'value' in res:
            res['value'] = {}
            
        route_param = self._default_route()
        if route_param:
            route_id = int(route_param)
            res['value']['route_id'] = route_id
        
        return res
          
sale_order_line()

