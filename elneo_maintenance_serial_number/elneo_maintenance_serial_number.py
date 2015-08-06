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

from openerp import models,fields,api, _


#When user confirm shop sale with a product with serial number required
class sale_order(models.Model):
    _inherit = 'sale.order'
    
    @api.multi
    def action_wait(self):
        res = super(sale_order,self).action_wait()
        
        for order in self:
            for line in order.order_line:
                if line.product_id.serialnumber_required:
                    wizard_id = self.env['serial.number.wizard'].create()
                    return {
                        'name':_("Serial numbers"),
                        'view_mode': 'form',
                        'view_type': 'form',
                        'res_id':wizard_id,
                        'res_model': 'serial.number.wizard',
                        'type': 'ir.actions.act_window',
                        'nodestroy': True,
                        'target': 'new',
                        'domain': '[]',
                        'context': dict(self.env.context, active_ids=self._ids)
                    }
        
        
        return res 
     
