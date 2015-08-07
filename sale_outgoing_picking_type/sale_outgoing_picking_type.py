# -*- coding: utf-8 -*-
from openerp import models,fields,api,osv
from datetime import datetime
from openerp.tools.translate import _

class sale_order(models.Model):
    _inherit = 'sale.order'
    outgoing_picking_type = fields.Many2one('stock.picking.type', string='Delivery type', domain=[('code','=','outgoing')])
sale_order()

class procurement_order(models.Model):
    _inherit = 'procurement.order'
    
    @api.model
    def _run_move_create(self, procurement):
        res = super(procurement_order, self)._run_move_create(procurement)
        if res['picking_type_id']:
            picking_type = self.env['stock.picking.type'].browse(res['picking_type_id'])
            sale_line = procurement.sale_line_id 
            if picking_type.code == 'outgoing' and sale_line and sale_line.order_id and sale_line.order_id.outgoing_picking_type:
                res['picking_type_id'] = sale_line.order_id.outgoing_picking_type.id
        return res
        
procurement_order()