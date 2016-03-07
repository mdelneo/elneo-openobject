# -*- coding: utf-8 -*-
##############################################################################
#
#    Elneo
#    Copyright (C) 2011-2015 Elneo (Technofluid SA) (<http://www.elneo.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp import models, fields, api, _



class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'
    
    maintenance_picking_type_id = fields.Many2one('stock.picking.type', string='Maintenance picking type')


class MaintenanceInterventionProduct(models.Model):
    _inherit = 'maintenance.intervention.product'
    
    @api.one
    def _get_allow_from_stock(self):
        res = False
        moves = self.env['stock.move'].search([('intervention_product_id','=',self.id)])
        moves_internal = moves.filtered(lambda r:r.picking_id.picking_type_id.code=='internal')
        
        if self in moves_internal.mapped('intervention_product_id'):
            res = False
        else:
            res = True
        
        return res
    
    allow_from_stock = fields.Boolean(string='Allow From stock',compute='_get_allow_from_stock')
    from_stock = fields.Boolean(string='From stock directly',help='Allows to take the product directly from stock to the customer.')

    @api.one
    def get_move_location_id(self):
        res = super(MaintenanceInterventionProduct,self).get_move_location_id
        
        if self.from_stock:
            res = self.intervention_id.sale_order_id.warehouse_id.lot_stock_id.id
        
        return res
        