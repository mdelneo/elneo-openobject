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
from openerp import models, fields, api


class MaintenanceIntervention(models.Model):
    _inherit='maintenance.intervention.product'
    
    warehouse_return = fields.Selection(compute='_get_return_allowed',selection=[('allowed','Allowed'),('avoid','Avoid'),('never','Never'),('unknown','Unknown')],string='Return Authorized',help='If true, the product is allowed to be returned to warehouse')
    
    @api.one
    def _get_return_allowed(self):

        if self.sale_order_line_id and self.sale_order_line_id.procurement_ids:
            if self.sale_order_line_id.procurement_ids.filtered(lambda r:r.purchase_id):
                '''
                We found a purchase
                '''
                if self.product_id and self.env['stock.warehouse.orderpoint'].search([('product_id','=',self.product_id.id),('warehouse_id','=',self.intervention_id.warehouse_id.id)]):
                    '''
                    We found an orderpoint rule (product is usually stocked)
                    '''
                    self.warehouse_return = 'allowed'
                else:
                    self.warehouse_return = 'never'
            else:
                '''
                Procurements are ok but no purchase found
                '''
                if self.product_id and self.env['stock.warehouse.orderpoint'].search([('product_id','=',self.product_id.id),('warehouse_id','=',self.intervention_id.warehouse_id.id)]):
                    self.warehouse_return = 'allowed'
                else:
                    self.warehouse_return = 'avoid'
        else:
            '''
            No procurements found
            '''
            self.warehouse_return = 'unknown'

        