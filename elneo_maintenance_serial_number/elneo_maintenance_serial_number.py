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
    def action_button_confirm(self):
        assert len(self) == 1, 'This option should only be used for a single id at a time.'
        mod_obj = self.env['ir.model.data']
        
        for order in self:
            if order.shop_sale:
                for line in order.order_line:
                    if line.product_id.serialnumber_required:
                        #wizard_id = self.env['serial.number.wizard'].with_context(active_ids=self._ids).create({})
                        
                        model_data = mod_obj.search([('model','=','ir.ui.view'),('name','=','serial_number_wizard_form_view')])
                        resource = model_data.res_id
                        
                        context = self.env.context.copy()
                         
                        return {
                            'name': _('Serial numbers'),
                            'view_type': 'form',
                            'context': context,
                            'view_mode': 'form',
                            'res_model': 'serial.number.wizard',
                            'views': [(resource,'form')],
                            'nodestroy':True,
                            #'res_id':wizard_id.id,
                            'type': 'ir.actions.act_window',
                            'target': 'new',
                            }
        
            res = super(sale_order,order).action_button_confirm()
        return res
