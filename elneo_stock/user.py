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


class res_users(models.Model):
    _inherit = 'res.users'
    
    default_warehouse_id = fields.Many2one('stock.warehouse','Default Warehouse',help='Default Warehouse to match some specific needs')
    
class sale_order(models.Model):
    _inherit = 'sale.order'
    
    def _get_default_warehouse(self):
        user_default_warehouse = self.env['res.users'].browse(self._uid).default_warehouse_id
        if user_default_warehouse:
            return user_default_warehouse
    
    warehouse_id = fields.Many2one(default=_get_default_warehouse)
    