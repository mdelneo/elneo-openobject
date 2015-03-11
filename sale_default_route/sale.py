# -*- coding: utf-8 -*-
from openerp import models, api

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
    
        res = super(sale_order_line,self).product_id_change(self.order_id.pricelist_id.id, self.product_id.id, self.product_uom_qty, False, self.product_uos_qty, False, self.name, self.order_id.partner_id.id, False, True, self.order_id.date_order, False, self.order_id.fiscal_position.id, False)
        
        self.select_route()
        
        if res.has_key('value'):
            values = res['value']
            for name in values :
                self[name] = values[name]
                    
        return res
                    
    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty(self):
  
        res = super(sale_order_line,self).product_uom_change(self.order_id.pricelist_id.id, self.product_id.id, self.product_uom_qty,self.product_uom.id, self.product_uos_qty, self.product_uos.id, self.name, self.order_id.partner_id.id, False, True, self.order_id.date_order)
        
        self.select_route()
        
        if res.has_key('value'):
            values = res['value']
            for name in values :
                self[name] = values[name]
                
        return res           
                    
    def select_route(self):
        route_stock = self.env['ir.config_parameter'].get_param('sale_default_route.sale_default_route_stock',False)
        route_no_stock = self.env['ir.config_parameter'].get_param('sale_default_route.sale_default_route_no_stock',False)
        
        if self.product_id and self.product_id.route_ids:
            qty = self.product_id.with_context({'warehouse':self.order_id.warehouse_id.id})._product_available()[self.product_id.id]
            
            if qty.has_key('virtual_available'):
                if (route_no_stock != 'False' and qty['virtual_available'] < self.product_uom_qty and int(route_no_stock) in self.product_id.route_ids.mapped('id')) :
                    self.route_id = int(route_no_stock)
                elif(route_stock != 'False' and qty['virtual_available'] >= self.product_uom_qty and int(route_stock) in self.product_id.route_ids.mapped('id')):
                    self.route_id = int(route_stock)

sale_order_line()

