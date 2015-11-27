# -*- coding: utf-8 -*-
from openerp import models,fields,api,osv
from datetime import datetime
from openerp.tools.translate import _
from openerp.exceptions import Warning, ValidationError

class sale_order(models.Model):
    _inherit = 'sale.order'
    outgoing_picking_type = fields.Many2one('stock.picking.type', string='Delivery type', domain=[('code','=','outgoing'),('special','=',True)])
    
    @api.one
    @api.constrains('outgoing_picking_type', 'carrier_id')
    def _check_carrier_id(self):
        if self.outgoing_picking_type and self.outgoing_picking_type.need_carrier and not self.carrier_id:
            raise ValidationError(_('You need to set a carrier for order %s.')%(self.outgoing_picking_type.name))
    
sale_order()

class stock_picking_type(models.Model):
    _inherit = 'stock.picking.type'
    special = fields.Boolean('Special', help="Special picking types can be selected in outgoing picking type of a sale.")
    need_carrier = fields.Boolean('Need carrier')
    
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