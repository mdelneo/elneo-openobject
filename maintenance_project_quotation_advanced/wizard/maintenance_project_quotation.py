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
from openerp.exceptions import Warning


class maintenance_project_quotation_wizard_element_detail(models.TransientModel):
    _name = 'maintenance.project_quotation_wizard.element_detail'
    
    wizard_id=fields.Many2one('maintenance.project_quotation_wizard', 'Wizard')
    sale_line_id=fields.Many2one('sale.order.line', 'Sale line')
    maintenance_element_id=fields.Many2one('maintenance.element', 'Maintenance element')
    product_code=fields.Char('Product',size=255)
    working_hours=fields.Integer('Working hours planned')
   
#Wizard to ask new maintenance quotation
class maintenance_project_quotation_wizard(models.TransientModel):
    _name='maintenance.project_quotation_wizard'
    
    @api.model
    def _default_elements_details(self):
        
        sale = self.env['sale.order'].browse(self.env.context.get('active_id',False))
        sale_order_lines = sale.order_line.filtered(lambda r:r.product_id.type=='product')
        #if installation already linked to sale 
        #sale_order_lines = self.env['sale.order.line'].search([('order_id','=',self.env.context['active_id']),('product_type','=','product')])
        res = []
        
        for line in sale_order_lines:
            elements = self.env['maintenance.element'].search([('sale_order_line_id','=',line.id)])
            for element in elements:
                if element.element_model_id.time_counter:
                    res.append({
                        'sale_line_id':element.sale_order_line_id.id, 
                        'product_code':element.sale_order_line_id.product_id.default_code, 
                        'working_hours':element.expected_time_of_use, 
                        'maintenance_element_id':element.id
                    })
        
            if line.product_uom_qty > len(elements):
                for i in range(0,int(line.product_uom_qty)-len(elements)): 
                    #check if product has maintenance element model with time_counter
                    self.env.cr.execute('select model_id from maintenance_element_model_product_rel rel left join maintenance_element_model m on m.id = rel.model_id where product_id = %s and m.time_counter',(line.product_id.id,))
                    if self.env.cr.fetchone():
                        res.append({
                            'sale_line_id':line.id,
                            'product_code':line.product_id.default_code,
                            'working_hours':0,
                        })
            
        return res
        
    elements_details=fields.One2many('maintenance.project_quotation_wizard.element_detail', 'wizard_id', 'Maintenance element details',default=_default_elements_details)   
        
    @api.multi
    def ask(self):
        
        for wizard in self:
            for detail in wizard.elements_details:
                if not detail.working_hours :
                    elements = detail.sale_line_id.product_id.maintenance_element_model_ids.sorted(key=lambda r:r.id, reverse=True)
                    if elements and elements[0].time_counter:
                        raise Warning(_('Please fill expected working hours for %s.')%(detail.sale_line_id.product_id.default_code,))
            
            
            #installation_pool = self.pool.get('maintenance.installation')
            
            if(self.env.context.get('active_id',False)==False):
                return False
            
            
            sale_order = self.env['sale.order'].browse(self.env.context.get('active_id',False))
            
            #If request for quotation has already been done, only update working hours of related maintenance elements 
            if sale_order.maintenance_project_id:
                for detail in wizard.elements_details:
                    if detail.maintenance_element_id:
                        detail.maintenance_element_id.expected_time_of_use=detail.working_hours
            
            
            #find good travel cost
            #TODO:
            '''
            change_address = self.env['maintenance.installation'].on_change_address_id(sale_order.partner_invoice_id.id)
            
            
            if change_address.has_key('value') and change_address['value'].has_key('travel_cost_id'):
                travel_cost_id = change_address['value']['travel_cost_id']
            else:
                travel_cost_id = None
            '''    
                
            
            if sale_order.installation_id:
                installation_id = sale_order.installation_id
            else:
                maintenance_installation = {
                    'partner_id':sale_order.partner_id.id,
                    'address_id':sale_order.partner_invoice_id.id,
                    'invoice_address_id':sale_order.partner_invoice_id.id,
                    'is_quotation_installation':True, 
                    #'travel_cost_id':travel_cost_id
                }
                
                installation_id = self.env['maintenance.installation'].create(maintenance_installation)
            
            
            sale_order_lines = self.env['sale.order.line'].search([('order_id','=',self.env.context.get('active_id',False)),('product_id.type','=','product')])
            
            maintenance_elements = []
            for order_line in sale_order_lines:
                number_of_elements_to_create = int(order_line.product_uom_qty)-len(order_line.maintenance_element_ids)
                
                #find working hours in current wizard
                working_hours = []
                for detail in wizard.elements_details:
                    if detail.sale_line_id.id == order_line.id and not detail.maintenance_element_id:
                        working_hours.append(detail.working_hours)
                
                for i in range(0,number_of_elements_to_create):
                    current_working_hours = working_hours and working_hours[i] or 0
                    self.env.cr.execute('select model_id from maintenance_element_model_product_rel where product_id = %s',(order_line.product_id.id,))
                    element_model_id = self.env.cr.fetchone()
                    
                    maintenance_element = {
                        'installation_id':installation_id.id,
                        'partner_id':order_line.order_partner_id.id,
                        'name':order_line.product_id.default_code,
                        'product_id':order_line.product_id.id, 
                        'expected_time_of_use':current_working_hours, 
                        'sale_order_line_id':order_line.id,
                        'element_model_id':element_model_id
                    }
                    maintenance_elements.append(maintenance_element)
            
            for maintenance_element in maintenance_elements:
                self.env['maintenance.element'].create(maintenance_element)
            
            maintenance_elements =  self.env['maintenance.element'].search([('installation_id','=',installation_id.id)])
            
            if not sale_order.maintenance_project_id:
                maintenance_project_id = self.env['maintenance.project'].create({'installation_id':installation_id.id,'maintenance_elements':[(4,elt_id.id) for elt_id in maintenance_elements]})
            else:
                maintenance_project_id = sale_order.maintenance_project_id
                sale_order.maintenance_project_id.installation_id = installation_id
                sale_order.maintenance_project_id.sale_order_id = sale_order
                sale_order.maintenance_project_id.maintenance_elements = maintenance_elements | sale_order.maintenance_project_id.maintenance_elements
                
            maintenance_project_id.signal_workflow('quotation_todo')
            installation_id.signal_workflow('installation_draft')
            
            sale_order.installation_id=installation_id
            sale_order.maintenance_project_id=maintenance_project_id
            
            context = self.env.context.copy()
        
            return {
                'name':_("New maintenance project"), 
                'view_mode': 'form',
                'view_id': False,
                'view_type': 'form',
                'res_model': 'maintenance.project',
                'res_id': maintenance_project_id.id,
                'type': 'ir.actions.act_window',
                'target': 'current',
                'domain': '[]',
                'context': context}
        
        return True
