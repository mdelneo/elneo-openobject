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
from openerp import models, api, _
from openerp.exceptions import Warning

class ElneoLandefeldSaleWizard(models.Model):
    _name = 'elneo_landefeld.sale.wizard'

    def _change_lines_route(self,sale_order):
        if sale_order and sale_order.order_line:
            #If Landefeld Drop Ship route is defined
            route = self.env['stock.location.route'].search([('landefeld_dropship','=',True)])
            if not route:
                # Take the first rule that correspond to Supplier => Customer
                rule = self.env['procurement.rule'].search([('picking_type_id.default_location_src_id.usage','=','supplier'),('picking_type_id.default_location_dest_id.usage','=','customer')],limit=1)
                if rule and rule.route_id:
                    route = rule.route_id
            if not route:
                raise Warning(_('There is no route defined to supply directly your customer from the supplier directly.\n\nPlease contact your administrator'))
            
            for line in sale_order.order_line:
                line.route_id = route
    
    
    @api.multi
    def action_confirm_landefeld(self):
        self.ensure_one()
        if self.env.context.get('active_model',False) != 'sale.order':
            return False
        sale_order = self.env['sale.order'].browse(self.env.context.get('active_ids',False))
        self._change_lines_route(sale_order)
        sale_order.landefeld_automatic_sale = True
        sale_order.signal_workflow('order_confirm')
        return {'type': 'ir.actions.act_window_close'}
    
    @api.multi
    def action_confirm_classic(self):
        self.ensure_one()
        if self.env.context.get('active_model',False) != 'sale.order':
            return False
        sale_order = self.env['sale.order'].browse(self.env.context.get('active_ids',False))
        sale_order.disable_automatic_landefeld = True
        sale_order.signal_workflow('order_confirm')
        
        return {'type': 'ir.actions.act_window_close'}
    