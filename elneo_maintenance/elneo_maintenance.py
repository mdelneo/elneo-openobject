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
import datetime
from openerp import models, fields, api, _
from openerp.exceptions import Warning
from ZSI.TC import Nilled

class maintenance_intervention_product(models.Model):
    _inherit = 'maintenance.intervention.product'
    
    @api.onchange('product_id')
    def _onchange_stock_product_id(self):
        self._get_stock_quantity()
    
    @api.one
    def _get_stock_quantity(self):
        if self.product_id:
            if self.intervention_id and self.intervention_id.sale_order_id:
                warehouse = self.intervention_id.sale_order_id.warehouse_id
            else:
                warehouse = self.env.user.default_warehouse_id
            
            if warehouse:    
                self.virtual_stock = self.product_id.with_context(location=warehouse.lot_stock_id.id).virtual_available
                self.real_stock = self.product_id.with_context(location=warehouse.lot_stock_id.id).qty_available
            else:
                self.virtual_stock = 0
                self.real_stock = 0
        else:
            self.virtual_stock = 0
            self.real_stock = 0
        
    
    @api.one
    def _qty_virtual_stock(self):
        self._get_stock_quantity()
        
    
    @api.one
    def _qty_real_stock(self):
        self._get_stock_quantity()
            
    @api.model
    def create(self,vals):
        if vals and 'route_id' not in vals:
            default_route = self.env['ir.config_parameter'].get_param('sale_default_route.default_route',False)
            if default_route:
                vals.update({'route_id':int(default_route)})
                
        return super(maintenance_intervention_product,self).create(vals)
            
    def _default_route(self):
        route_id = self.env['ir.config_parameter'].get_param('sale_default_route.default_route',False)
        if not (type(route_id) is int):
            try:
                route_id = int(route_id)
            except Exception,e:
                route_id = None
        return route_id
    
    @api.model
    def default_get(self, fields_list):
        res = super(maintenance_intervention_product,self).default_get(fields_list)
        if 'route_id' in fields_list:
            res['route_id'] = self._default_route()
        return res
   
    virtual_stock = fields.Float(compute='_qty_virtual_stock',  string='Virtual stock')
    real_stock = fields.Float(compute='_qty_real_stock',  string='Real stock')
    procurement_path = fields.Char(related='sale_order_line_id.procurement_path', string='Procurement path')
    
    
class maintenance_installation(models.Model):
    _inherit='maintenance.installation'
    
    maintenance_product_description=fields.Text("Maintenance products description")
    
class maintenance_intervention(models.Model):
    _inherit='maintenance.intervention'
    
    @api.multi
    def write(self,vals):
        res = super(maintenance_intervention, self).write(vals)
        if 'contact_address_id' in vals:            
            for intervention in self:
                if intervention.sale_order_id:
                    intervention.sale_order_id.quotation_address_id = vals['contact_address_id']
        return res
    
    @api.onchange('installation_id')
    def on_change_installation_id_elneo(self):
        '''
        @depends: account_block_partner
        '''
        res={}
        if self.installation_id and self.installation_id.partner_id and self.installation_id.partner_id.blocked:
            res['warning'] = {
                    'title': _("Warning: Customer blocked")+' \n' ,
                    'message': _("Warning: The Customer is blocked")+' \n'}
        return res
    
    @api.multi
    def action_convert_delivery(self):
        #cancel interventions
        self.write({'state': 'cancel'})
        
    @api.model
    def get_sale_order_line(self,sale_order, intervention_product, partner):

        order_line = super(maintenance_intervention,self).get_sale_order_line(sale_order,intervention_product,partner)
        
        if intervention_product.route_id:
            route_id = intervention_product.route_id.id
        else:
            route_id = self.env['ir.config_parameter'].get_param('sale_default_route.default_route',False)
            route_id = int(route_id)
            
        order_line['route_id'] = route_id
        
        return order_line
    
    @api.multi
    def action_create_update_sale_order(self):
        return super(maintenance_intervention,self.with_context(from_intervention=True)).action_create_update_sale_order()
        

    installation_zip = fields.Char(related='installation_id.address_id.zip', string="Zip", store=True)
    blocked = fields.Boolean(related='partner_id.blocked', string='Customer blocked')
    
    @api.one
    def extract_date_from_datetime(self):
        if self.date_start:
            self.date_start_date = fields.Date.from_string(self.date_start)
        else:
            self.date_start_date = ''
           
    date_start_date = fields.Date(string="date_start_date", compute='extract_date_from_datetime')
    
class maintenance_element(models.Model):
    _inherit = 'maintenance.element'
    
    @api.multi
    def import_timeofuse(self):
        
        return {
                'name':_("Import time of use"),
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'maintenance.element.timeofuse.wizard',
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': '[]',
                'context': dict(self.env.context, active_ids=self._ids)
            }
        
    @api.one
    @api.depends('maintenance_projects')
    def _is_under_project(self):
        for project in self.maintenance_projects:
            if project.active:
                for project_elt in project.maintenance_elements:
                    if project_elt.id == self.id: 
                        self.is_under_project = True
            break

      
    power = fields.Float("Power (kW)")
    maintenance_partner = fields.Char(string="Maintenance partner", size=255)
    under_competitor_contract = fields.Boolean("Under competitor contract")
    end_of_current_contract = fields.Date('End of current contract')
    supplier_id = fields.Many2one('res.partner', string='Supplier')
    under_project = fields.Boolean(compute=_is_under_project,  string="Under project", readonly=True, store=True)                                                    
    

    
class maintenance_project(models.Model):
    _inherit = 'maintenance.project'
    
    intervention_months = fields.Text("Intervention months")
    annual_visits_number = fields.Integer("Number of annual visits")
    machines = fields.Text("Machines", readonly=False)        
    nom_visual = fields.Char("Nom visual", size=255, readonly=True)
    entreprise_visual = fields.Text("Entreprise visual", readonly=True)
    client_visual = fields.Char("Client visual", size=255, readonly=True)
    personne_visual = fields.Char("Personne visual", size=255, readonly=True)
    

class stock_warehouse(models.Model):
    _inherit = 'stock.warehouse'
    
    maintenance_picking_type_id = fields.Many2one('stock.picking.type', string='Maintenance picking type')
        

class sale_order(models.Model):
    _inherit='sale.order'
    
    @api.multi
    def action_ship_create(self):
        result = super(sale_order, self).action_ship_create()
        for order in self:
            if order.intervention_id:
                picks = []
                order.intervention_id.state = 'confirmed'
                #find pickings:
                if order.procurement_group_id:
                    picks = set()
                    for proc in order.procurement_group_id.procurement_ids:
                        for move in proc.move_ids:
                            picks.add(move.picking_id)
                    picks = list(picks)
                else:
                    picks = order.picking_ids
                if picks:
                    for pick in picks:
                        if pick.picking_type_id.code == 'outgoing':
                            pick.picking_type_id = order.warehouse_id.maintenance_picking_type_id
          
        return result
    
    
    @api.model
    def copy(self,default=None):
        if self.intervention_id:
            return super(sale_order,self.with_context(from_intervention=True)).copy(default=default)
        else:
            return super(sale_order,self).copy(default=default)
        
    @api.one
    def _check_carrier_id(self):
        if not self.env.context.get('from_intervention', False):
            return super(sale_order,self)._check_carrier_id()
        else:
            return True
            
    
    @api.multi
    def action_button_confirm(self):
        for sale in self:
            if not sale.shop_sale:
                for line in sale.order_line:
                    if line.product_id.maintenance_product and len(line.maintenance_element_ids) < line.product_uom_qty:
                        dummy, view_id = self.env['ir.model.data'].get_object_reference('elneo_maintenance', 'view_wizard_sale_confirm')
                        
                        context = self.env.context.copy()
                        context['partner_id'] = sale.partner_id.id
                        context['sale_id'] = sale.id 
                        return {
                                'name':_("Sale confirm"),
                                'view_mode': 'form',
                                'view_id': [view_id], 
                                'view_type': 'form',
                                'res_model': 'wizard.sale.confirm',
                                'type': 'ir.actions.act_window',
                                'target': 'new',
                                'nodestroy':True, 
                                'context':context
                            }
            
        return super(sale_order, self).action_button_confirm()

class stock_move(models.Model):
    _inherit = 'stock.move'
    
    @api.multi
    def unlink(self):
        #bypass draft verification if we delete maintenance move
        try:
            return super(stock_move, self).unlink()
        except Warning, e:
            if e.value == _('You can only delete draft moves.'): 
                for move in self:
                    if move.picking_id and move.picking_id.sale_id and move.picking_id.sale_id.intervention_id:
                        return super(models.Model,self).unlink()
            raise e
        
    @api.one
    @api.depends('move_dest_id')
    def get_is_purchased(self):
        if self.search([('move_dest_id','=',self.id)]):
            self.purchased = True
        else:
            self.purchased = False
    
    #sale_price and purchased are used in reservation report
    sale_price = fields.Float(related='procurement_id.sale_line_id.price_unit', string="Sale price") 
    purchased = fields.Boolean(compute=get_is_purchased, string="Is purchased", store=True)

'''
class maintenance_installation(osv.osv):
    _inherit = 'maintenance.installation'
    
    def onchange_address_id(self, cr, uid, ids, address_id, context=None):
        user_pool = self.pool.get("res.users")
        if address_id:
            seller_id = self.pool.get("sale.order").find_sale_man_id(cr, uid, address_id, 10)
            if not seller_id:
                seller_id = self.pool.get("sale.order").find_sale_man_id(cr, uid, address_id, 11)
            if seller_id:
                shop_id = user_pool.browse(cr, uid, seller_id, context=context).shop_id.id
                return {'value':{'shop_id':shop_id}}
        return {}
    
    
    
    
maintenance_installation()

class sale_order(osv.osv):
    _inherit = 'sale.order'
    
    def write(self, cr, uid, ids, vals, context=None):
        if vals.get("intervention_id",False):
            vals['disable_automatic_landefeld'] = True
        return super(sale_order, self).write(cr, uid, ids, vals, context=context)
    
    def create(self, cr, user, vals, context=None):
        if vals.get("intervention_id",False):
            vals['disable_automatic_landefeld'] = True
        return super(sale_order, self).create(cr, user, vals, context=context)

sale_order()

class maintenance_intervention(osv.osv):
    _inherit = 'maintenance.intervention' 
    
    _columns = {       
        'create_uid': fields.many2one('res.users', 'Creation user', readonly=True),
        'write_uid':  fields.many2one('res.users', 'Last Modification User', readonly=True),
       
    }
    
    
    # TO CHECK
    #_order = 'date_scheduled desc NULLS LAST'
    
    def write(self, cr, uid, ids, vals, context={}):
        res = super(maintenance_intervention, self).write(cr, uid, ids, vals, context)
        if 'contact_address_id' in vals:
            sale_order_pool = self.pool.get("sale.order")            
            for intervention in self.browse(cr, uid, ids, context):
                if intervention.sale_order_id:
                    sale_order_pool.write(cr, uid, [intervention.sale_order_id.id], {'quotation_address_id':vals['contact_address_id']}, context=context)
        return res
    
  
    
    def get_sale_default_values(self, cr, uid, partner, intervention, context):
        res = super(maintenance_intervention, self).get_sale_default_values(cr, uid, partner, intervention, context)
        if context.get("quotation",False) and intervention and intervention.contact_address_id:
            res['quotation_address_id'] = intervention.contact_address_id.id
        return res
    
    #Cancel intervention without sale_order
    def action_convert_delivery(self, cr, uid, ids, context=None):
        #cancel interventions
        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
        return True
    
    def generate_invoice(self, cr, uid, ids, context):
        res = super(maintenance_intervention, self).generate_invoice(cr, uid, ids, context)
        
        #manage cost price of invoice lines and section_id of invoice
        if res:
            invoice_line_pool = self.pool.get("account.invoice.line")
            invoice_pool = self.pool.get("account.invoice")
            for invoice in invoice_pool.browse(cr, uid, res, context=context):
                #set cost price from sale order line if exist or from product else
                for invoice_line in invoice.invoice_line:
                    if invoice_line.sale_order_lines:
                        invoice_line_pool.write(cr, uid, [invoice_line.id], {"cost_price":invoice_line.sale_order_lines[0].purchase_price}, context=context)
                    else:
                        invoice_line_pool.write(cr, uid, [invoice_line.id], {"cost_price":invoice_line.product_id.cost_price}, context=context)
                        
                #set section_id of sale order
                if invoice.sale_order_ids:
                    invoice_pool.write(cr, uid, [invoice.id], {'section_id':invoice.sale_order_ids[0].section_id.id}, context=context)
        
        return res

class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    
    def _get_installation(self, cr, uid, ids, field_names, args, context=None):
        res = {}
        for pick in self.browse(cr, uid, ids, context):
            res[pick.id] = {}
            if pick.sale_id and pick.sale_id.intervention_id:
                if 'is_maint_reservation' in field_names:
                    res[pick.id]['is_maint_reservation'] = True
                if 'installation_id' in field_names:
                    if pick.sale_id.intervention_id.state != 'cancel':
                        res[pick.id]['installation_id'] = pick.sale_id.intervention_id.installation_id.id
                    else:
                        res[pick.id]['installation_id'] = None
            else: 
                if 'is_maint_reservation' in field_names:
                    res[pick.id]['is_maint_reservation'] = False
        return res
    
    def _get_reservation_by_sale_order(self, cr, uid, ids, context=None):
        res = []
        for sale in self.pool.get("sale.order").browse(cr, uid, ids, context):
            res.extend([pick.id for pick in sale.picking_ids])
        return res
    
    def _get_reservation_by_intervention(self, cr, uid, ids, context=None):
        res = []
        for intervention in self.pool.get("maintenance.intervention").browse(cr, uid, ids, context):
            if intervention.sale_order_id.id:
                res.extend(self.pool.get("stock.picking")._get_reservation_by_sale_order(cr, uid, [intervention.sale_order_id.id], context))
        return res
    
    _columns={
        'is_maint_reservation':fields.function(_get_installation, string='Maintenance reservation', type="boolean", method=True, store={
                'sale.order': (_get_reservation_by_sale_order, ['intervention_id'], 20),
                'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['sale_id'], 20),
                'maintenance.intervention':(_get_reservation_by_intervention, ['sale_order_id','state'], 10)
            }, multi='installation'),
               
        'maint_color':fields.related('sale_id', 'intervention_id', 'maint_type', 'color', type='char', size=255, string='Color (maintenance)'),  
        'maint_type':fields.related('sale_id', 'intervention_id', 'maint_type', type='many2one', relation='maintenance.intervention.type', string="Maintenance type"),
        'installation_id':fields.function(_get_installation, string="Installation", type='many2one', method=True, relation='maintenance.installation', multi='installation', store={
            'sale.order': (_get_reservation_by_sale_order, ['intervention_id'], 20),
            'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['sale_id'], 20),
        }), 
    }
stock_picking()



class maintenance_project_initial_cpi_id_compute(osv.osv_memory):
    
    _name = 'maintenance.project.initial.cpi.compute'
    
    def compute(self, cr, uid, ids, context=None):
        project_pool = self.pool.get("maintenance.project")
        cpi_pool = self.pool.get("cpi.be.entry")
        for project in project_pool.browse(cr, uid, context.get("active_ids"), context):
            if project.date_start and project.cpi_type_id:
                year = datetime.strptime(project.date_start, '%Y-%m-%d').year
                month = datetime.strptime(project.date_start, '%Y-%m-%d').month
                cpi_id = cpi_pool.search(cr, uid, [('type_id','=',project.cpi_type_id.id), ('year','=',year),('month','=',month)], context=context)
                if cpi_id:
                    project_pool.write(cr, uid, project.id, {'initial_cpi_id':cpi_id[0]}, context=context)
        return {'type': 'ir.actions.act_window_close'}
maintenance_project_initial_cpi_id_compute()

    
    def action_create_update_sale_order(self, cr, uid, ids, context):
        sale_order_pool = self.pool.get("sale.order")
        result = super(maintenance_project, self).action_create_update_sale_order(cr, uid, ids, context)
        for project in self.browse(cr, uid, ids, context):
            sale_order = project.sale_order_id
            if sale_order:
                #find sale_man
                dpt = 10
                shop_id = 1
                sale_man_id = sale_order_pool.find_sale_man_id(cr, uid, sale_order.partner_invoice_id.id, dpt)
                if not sale_man_id:
                    dpt = 11
                    shop_id = 2
                    sale_man_id = sale_order_pool.find_sale_man_id(cr, uid, sale_order.partner_invoice_id.id, dpt)
                sale_order_pool.write(cr, uid, sale_order.id, {'shop_id':shop_id,'user_id':sale_man_id, 'section_id':dpt}, context=context)
                sale_order_pool.order_confirm_elneo(cr, uid, [sale_order.id], context=context)
        return result
    
    def get_sale_order_lines(self, cr, uid, ids, context):
        result = super(maintenance_project, self).get_sale_order_lines(cr, uid, ids, context)
        for project in self.browse(cr, uid, ids, context):
            for line in result:
                line['price_unit'] = project.annual_amount
        return result
    
    
maintenance_project()


'''