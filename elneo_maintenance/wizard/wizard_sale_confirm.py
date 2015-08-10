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

class wizard_sale_confirm(models.TransientModel):
    _name = 'wizard.sale.confirm'
    
    @api.one
    def _get_default_installation(self):
        '''
        Looks for first installation for defined partner
        '''
        if 'partner_id' in self.env.context:
            installation_ids = self.env['maintenance.installation'].search([('partner_id','=',self.env.context['partner_id'])])
            if len(installation_ids) == 1:
                self.installation_id = installation_ids[0]
            else:
                self.installation_id=None

    installation_id = fields.Many2one('maintenance.installation', 'Installation',default=_get_default_installation)
    
    @api.multi
    def validate(self):
        for wizard in self:
            sale = self.env['sale.order'].browse(self.env.context.get("sale_id", False))
            sale.installation_id = wizard.installation_id
            
            for line in sale.order_line:
                if line.product_id.maintenance_product:
                    #find maintenance element model associated with product of line
                    self.env.cr.execute('select model_id from maintenance_element_model_product_rel where product_id = %s', (line.product_id.id,))
                    model_id = self.env.cr.fetchone()
                    if model_id:
                        model_id = model_id[0]
                    
                    for i in range(0,int(line.product_uom_qty)):
                        maintenance_element = {
                            'installation_id':wizard.installation_id.id,
                            'name':line.product_id.default_code,
                            'product_id':line.product_id.id, 
                            'sale_order_line_id':line.id, 
                            'element_model_id':model_id,                             
                        }
                        
                        if line.product_id.maintenance_element_type_id:
                            maintenance_element['element_type_id'] = line.product_id.maintenance_element_type_id.id
                            
                        if line.product_id.default_supplier_id:
                            maintenance_element['supplier_id'] = line.product_id.default_supplier_id.id 
                             
                        self.env['maintenance.element'].create(maintenance_element)
        
        sale = self.env['sale.order'].browse(self.env.context.get("sale_id", False))
        if sale:
            sale.signal_workflow('order_confirm')
        
        return {'type': 'ir.actions.act_window_close'}    
