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


class maintenance_installation(models.Model):
    _inherit = 'maintenance.installation'
    
    maintenance_projects=fields.One2many('maintenance.project', 'installation_id', 'Projects', domain=['|',('state','=','active'),('sale_order_id','=',False)])
    

class maintenance_element(models.Model):
    _inherit = 'maintenance.element'
    
    @api.one
    @api.depends('maintenance_projects.installation_id')
    def _is_with_project(self):
        
        if(len(self.env['maintenance.project'].search([('installation_id','=',self.installation_id.id)])) > 0):
            self.with_project=True
        else:
            self.with_project=False
        
    
    maintenance_projects=fields.Many2many("maintenance.project", 'maintenance_project_elements', 'element_id', 'project_id', "Maintenance projects")
    expected_time_of_use=fields.Integer("Annual expected hour of use")
    with_project=fields.Boolean(compute=_is_with_project, string="Under contract", store=True)
    
class maintenance_project_type(models.Model):
    _name = 'maintenance.project.type'
    
    name = fields.Char("Name", translate=True, size=255)
    product_id=fields.Many2one("product.product", string="Product")
    project_type_lines=fields.One2many('maintenance.project.type.line', 'project_type_id', 'Invoiced categories')
    budget_rules=fields.One2many('maintenance.project.budget.rule','project_type_id','Budget rules')
        

class maintenance_project_delay(models.Model):
    _name = 'maintenance.project.delay'
    
    name=fields.Char("Name", translate=True, size=255)
    price=fields.Float("Price")
     

class maintenance_project_type_line(models.Model):
    _name = 'maintenance.project.type.line'
    
    project_type_id=fields.Many2one('maintenance.project.type', string="Project type")
    product_category_id=fields.Many2one('product.category', string="Product category")
    intervention_type_id=fields.Many2one('maintenance.intervention.type', string='Intervention type', required=True)
    invoiced_percent=fields.Float('Invoiced percent')
    

class maintenance_project_budget_line_type(models.Model):
    _name='maintenance.project.budget.line.type'
    
    name=fields.Char('Name', size=255,translate=True) 
    display_on_contract=fields.Boolean('Display on contract', help="Lines of this type are displayed on printed contracts")


class maintenance_project_budget_line(models.Model):
    _name = 'maintenance.project.budget.line'
         
    #When project is validated, in accordance with budget type and project type, say if line is included in contract price or not
    @api.one
    def _get_included(self):
        self.included = False
       
    
    project_id = fields.Many2one('maintenance.project', string="Project", required="True")
    element_id=fields.Many2one('maintenance.element', string="Maintenance element")
    product_id=fields.Many2one('product.product', string="Product")
    quantity=fields.Float(string='Quantity')
    name=fields.Char('Name', size=255) 
    sale_price=fields.Float('Sale price')
    cost_price=fields.Float('Cost price')
    budget_line_type_id=fields.Many2one('maintenance.project.budget.line.type', 'Type')
    maintenance_product_id=fields.Many2one('maintenance.intervention.product', string='Maintenance Product')
    included=fields.Boolean(compute=_get_included, readonly=True, string="Included", help="When project is validated, in accordance with budget type and project type, say if line is included in contract price or not.") 
    intervention_id=fields.Many2one('maintenance.intervention', string="Intervention", help="Intervention generated (among other) by this project detail.")
    intervention_code=fields.Char(related='intervention_id.code',string='Intervention',readonly=True)
    time_of_use=fields.Float('Time of use')
    intervention_type_id=fields.Many2one('maintenance.intervention.type', string='Intervention type', required=True)


class maintenance_project_budget_rule(models.Model):
    _name = 'maintenance.project.budget.rule'
    
    project_type_id=fields.Many2one('maintenance.project.type', 'Project type', required=True)
    intervention_type_id=fields.Many2one('maintenance.intervention.type', 'Project type', required=True)  
    budget_line_type_id=fields.Many2one('maintenance.project.budget.line.type', 'Budget line type', required=True)
    included=fields.Boolean('Included', required=True)
    
maintenance_project_budget_rule()


class maintenance_project(models.Model):
    _name = 'maintenance.project'
    _rec_name = 'code'
    
    _inherit=['mail.thread','ir.needaction_mixin']
    
    @api.one
    def unlink(self):
        
        if self.state == 'active':
            raise Warning(_('Please disable maintenance project %s before delete it.')%(self.code,))
        
        return super(maintenance_project, self).unlink()
    
    @api.one
    def draft(self):
        self.state = 'draft'
        return True
    
    @api.one
    def active(self):
        self.state='active'
        return True
    
    @api.one
    def disabled(self):
        self.state='disabled'
        return True
    
    @api.one
    def _get_interventions(self):
        filters = [("installation_id",'=',self.installation_id.id),('state','=','done')]
        if self.date_start:
            filters.append(('date_start','>',self.date_start))
        if self.date_end:
            filters.append(('date_start','<',self.date_end))
            
        self.interventions = self.env['maintenance.intervention'].search(filters)
        
        
    code=fields.Char("Code", size=255, index=True,default=lambda obj: obj.env['ir.sequence'].get('maintenance.project'))
    project_type_id=fields.Many2one('maintenance.project.type', string="Type", index=True, required=True)
    installation_id=fields.Many2one('maintenance.installation', string="Installation", index=True, required=True,track_visibility='onchange')  
    intervention_delay_id=fields.Many2one('maintenance.project.delay', string="Intervention delay", index=True, required=True) 
    note=fields.Text("Notes")        
    date_start=fields.Date('Start date')
    date_end=fields.Date('End date')
    sale_order_id=fields.Many2one('sale.order', string="Sale order", index=True, readonly=True,track_visibility='onchange') 
    #enable=fields.Boolean('Active', index=True,default=False)
    invoices=fields.Many2many(related="sale_order_id.invoice_ids", string="Invoices", readonly=True)
    interventions=fields.One2many("maintenance.intervention",compute=_get_interventions, string="Interventions history", readonly=True)
    maintenance_elements=fields.Many2many("maintenance.element", 'maintenance_project_elements', 'project_id', 'element_id', "Maintenance elements")
    state=fields.Selection([('draft','Draft'),('active','Active'),('disabled','Disabled')],'Status',readonly=True,translate=True,default='draft',track_visibility='onchange')
    budget_lines=fields.One2many('maintenance.project.budget.line', 'project_id', string='Budget lines')
    warehouse_id=fields.Many2one(related='installation_id.warehouse_id', relation='stock.warehouse', string='Warehouse', readonly=True)    
   

    #check if other projects are enable in the same time
    @api.multi
    @api.constrains('date_start','date_end','installation_id')
    def _check_contract_dates(self):
        for project in self: 
            if not project.state=='active' or not project.date_start or not project.date_end or not project.installation_id:    
                continue
            else:
                for install_project in project.installation_id.maintenance_projects:                
                    if install_project.state=='active' and project.state=='active' and \
                        ((install_project.date_start < project.date_end and install_project.date_start > project.date_end) or (install_project.date_end < project.date_end and install_project.date_end > project.date_start) or \
                        (project.date_start < install_project.date_end and project.date_start > install_project.date_end) or (project.date_end < install_project.date_end and project.date_end > install_project.date_start)):
                        raise Warning(_('Several maintenance projects are active during the same period'))
        return True

    @api.one
    def get_sale_order_lines(self):
       
        sale_order = self.sale_order_id
        partner = sale_order.partner_id
        
        order_line = self.env['sale.order.line'].product_id_change( 
                                sale_order.pricelist_id.id, self.project_type_id.product_id.id, qty=1, 
                                partner_id=partner.id, lang=partner.lang, fiscal_position=sale_order.fiscal_position.id)['value']
        
        for field in order_line.keys():
            if type(order_line[field]) == list:
                field_type = self.env['sale.order.line']._columns[field]._type
                if field_type == 'one2many':
                    order_line[field] = [(0,0,val) for val in order_line[field]] 
                elif field_type == 'many2many':
                    order_line[field] = [(4,val) for val in order_line[field]]
        
        order_line['product_id'] = self.project_type_id.product_id.id
        order_line['product_uom_qty'] = 1
        order_line['order_id'] = sale_order.id
        return order_line

    
    @api.multi
    def action_create_update_sale_order(self): 
        #create sale_order
        for project in self:
            if not project.installation_id:
                continue
            
            partner = project.installation_id.partner_id
            #sale_order_line_pool = self.pool.get("sale.order.line")
            #sale_order_pool = self.pool.get("sale.order")
            
            if project.sale_order_id:
                if project.sale_order_id.state != 'draft':
                    raise Warning(_('Sale order is already confirmed.'))
                else:
                    project.sale_order_id.unlink()
                
            default_values = self.env['sale.order'].onchange_partner_id(partner.id)['value']
            
            invoice_address_id = None
            if project.installation_id.invoice_address_id:
                invoice_address_id = project.installation_id.invoice_address_id.id
            else:
                invoice_address_id = default_values['partner_invoice_id']
                
            delivery_address_id = None
            if project.installation_id.address_id:
                delivery_address_id = project.installation_id.address_id.id
            else:
                delivery_address_id = default_values['partner_shipping_id']
                
            '''
            contact_address_id = None
            if project.installation_id.contact_address_id:
                contact_address_id = project.installation_id.contact_address_id.id
            else:
                contact_address_id = default_values['partner_order_id']
                
            '''           
            default_values['partner_id'] = partner.id
            default_values['partner_invoice_id'] = invoice_address_id
            #default_values['partner_order_id'] = contact_address_id
            default_values['partner_shipping_id'] = delivery_address_id
            default_values['order_policy'] = 'manual'
            default_values['invoice_quantity'] = 'procurement'
            
            for field in default_values.keys():
                if type(default_values[field]) == list:
                    field_type = self.env['sale.order']._columns[field]._type
                    if field_type == 'one2many':
                        default_values[field] = [(0,0,val) for val in default_values[field]] 
                    elif field_type == 'many2many':
                        default_values[field] = [(4,val) for val in default_values[field]]
            
            sale_order = self.env['sale.order'].create(default_values)
            self.sale_order_id=sale_order
            self.state='active'
            
            
            #create sale order lines from maintenance intervention products of current intervention
            order_lines = self.get_sale_order_lines()
            for order_line in order_lines:                
                self.env['sale.order.line'].create(order_line)
                    
        return True
    
    @api.model
    def get_invoiced_percent(self,project_id, product_id, intervention_type_id):
        def get_percent_invoiced(product_categ, project, intervention_type_id, lowest_percent=float('inf')):
            if not product_categ:
                if lowest_percent == float('inf'):
                    lowest_percent = 100
                return lowest_percent
            
            for line in project.project_type_id.project_type_lines:
                if line.product_category_id.id == product_categ.id and line.intervention_type_id.id == intervention_type_id and line.invoiced_percent < lowest_percent:
                    lowest_percent = line.invoiced_percent
            
            return get_percent_invoiced(product_categ.parent_id, project, intervention_type_id, lowest_percent)
    
        if product_id and project_id:
            product = self.env['product.product'].browse(product_id)
            project = self.browse(project_id)
            invoiced_percent = get_percent_invoiced(product.categ_id, project, intervention_type_id)
            return invoiced_percent
        
        return 100



class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line' 
    
    @api.one
    def get_maintenance_invoiced_percent(self):
        if not self.invoice_id or self.invoice_id.type != 'out_invoice' or not self.intervention_id or not self.intervention_id.maintenance_project_id:
            self.maintenance_invoiced_percent=100
        else:
            self.maintenance_invoiced_percent = self.env['maintenance.project'].get_invoiced_percent(self.intervention_id.maintenance_project_id.id, self.product_id.id, self.intervention_id.maint_type.id)
    
    maintenance_invoiced_percent=fields.Float(compute=get_maintenance_invoiced_percent, string="Percent invoiced (if intervention)")


class account_invoice(models.Model):
    _name='account.invoice'
    _inherit = ['account.invoice','ir.needaction_mixin']
    
    @api.model
    def _needaction_domain_get(self):
        return ['&',('section_id.member_ids','in', self.env.uid),('state','=', 'draft')]
    
    @api.model
    def _needaction_count(self, domain):
        res = super(account_invoice, self)._needaction_count(domain)
        return res
    
    def _refund_cleanup_lines(self, cr, uid, lines):
        res = super(account_invoice, self)._refund_cleanup_lines(cr, uid, lines)
        for line in res:
            invoice_line = line[2]
            if invoice_line and invoice_line.has_key("intervention_product_id"):
                del invoice_line['intervention_product_id']
            if invoice_line and invoice_line.has_key("intervention_id"):
                del invoice_line['intervention_id']
        return res
    
  
    @api.one
    def _get_maintenance_projects(self):
       
        self.maintenance_projects = self.env['maintenance.project'].search( [('sale_order_id.invoice_ids','in',[so for so in self.ids])])
        
    @api.multi
    def _search_projects(self,operator,value):
        if (operator == '!=' and value == False):
            '''projects = self.env['maintenance.project'].search([('sale_order_id.invoice_ids','in',[so for so in self.ids])])'''
            
            self.env.cr.execute("""SELECT ai.id FROM account_invoice ai 
                                    JOIN sale_order_invoice_rel soir ON ai.id = soir.invoice_id 
                                    JOIN sale_order so ON soir.order_id = so.id
                                    JOIN maintenance_project mp ON mp.sale_order_id = so.id""")
            
            ids = self.env.cr.fetchall()
            return [('id','in',ids)]
            
        
        return []
    
    
    maintenance_projects=fields.Many2many('maintenance.project',compute=_get_maintenance_projects, search=_search_projects,string="Maintenance projects",readonly=True)
    
    
    

class maintenance_intervention(models.Model):
    _inherit = 'maintenance.intervention'
    
    
    @api.one
    @api.depends('tasks.date_start')
    def get_maintenance_project(self):
       
        project = self.compute_project(date_start=False, installation_id=False, intervention_id=self.id)

        self.maintenance_project_id = project
        
        if self.maintenance_project_id and self.maintenance_project_id.project_type_id:
            self.maintenance_project_type = project.project_type_id
        else:
            self.maintenance_project_type = None
        
    @api.one
    @api.onchange('tasks')
    def on_change_compute_tasks(self):
        res = self.on_change_compute_project()
        return res
    
    @api.one
    @api.onchange('installation_id')
    def on_change_compute_installation_id(self):
        res = self.on_change_compute_project()
        return res
    
    @api.one
    def on_change_compute_project(self):
        res = {}
        if False and self.tasks and self.tasks[0] and self.tasks[0][0] in [1,0] and self.tasks[0][2] and self.tasks[0][2]['date_start']:
            date_start = self.tasks[0][2]['date_start']
            project = self.compute_project(date_start, self.installation_id)

            self.maintenance_project_id=project.id
            self.maintenance_project_type = project.project_type_id.name
            
        return res
    
    
    @api.model
    @api.returns('maintenance.project')
    def compute_project(self,date_start=False, installation_id=False, intervention_id=False, state=False):
        '''
        @return: maintenance.project
        '''
        res = None
        #we could pass intervention_id as parameter instead of date_start and installation_id
        if not installation_id or not date_start:
            if not intervention_id:
                return res
            else:
                intervention = self.browse(intervention_id)
                date_start = intervention.date_start
                installation_id = intervention.installation_id.id
       
       
        search_filter = [('installation_id','=',installation_id),('date_start','<',date_start),'|',('date_end','>',date_start),('date_end','=',None)]
        
        #enable = None : don't filter on "enable" field
        if state:
            search_filter.append(('state','=',state))
        maintenance_project_ids = self.env['maintenance.project'].search(search_filter)
        '''if len(maintenance_project_ids) > 1:
            installation = self.pool.get("maintenance.installation").browse(cr, uid, installation_id, context=context)
            raise osv.except_osv(_('UserError'), _('Several projects for installation %s (%s) from %s')%(installation.name, installation.code, date_start))
        elif len(maintenance_project_ids) == 1:'''
        if len(maintenance_project_ids) > 0:
            return maintenance_project_ids[0]
        else:
            return res
    
    maintenance_project_id=fields.Many2one(comodel_name='maintenance.project',compute=get_maintenance_project, string='Maintenance project',  readonly=True, store=True)
    maintenance_project_type=fields.Many2one(comodel_name='maintenance.project.type',compute=get_maintenance_project, string='Project type',  readonly=True, store=True)
    
        
    @api.one
    def generate_invoice(self):
        invoices = super(maintenance_intervention, self).generate_invoice()
        #invoice_line_pool = self.pool.get("account.invoice.line")
        #project_pool = self.pool.get("maintenance.project")
        
        #change sale_price of account_invoice lines in accordance with maintenance_project type
        for invoice in invoices:
            for invoice_line in invoice.invoice_line:
                maintenance_product = invoice_line.intervention_product_id
                if maintenance_product:
                    invoiced_percent = maintenance_product.project_percent_invoiced
                else:
                    if self.maintenance_project_id:
                        invoiced_percent = self.env['maintenance.project'].get_invoiced_percent(self.maintenance_project_id.id, invoice_line.product_id.id, self.maint_type.id)
                    else:
                        invoiced_percent = 100
                
                if invoiced_percent != 100:
                    new_unit_price = (invoiced_percent/100)*invoice_line.price_unit
                    invoice_line.price_unit = new_unit_price
                    
        return invoices


class maintenance_intervention_product(models.Model):
    _inherit = 'maintenance.intervention.product'
    
    @api.one
    def get_project_percent_invoiced(self):

        intervention = self.intervention_id
        project = intervention.maintenance_project_id
        
        if not project:
            self.project_percent_invoiced = 100
        else:
            invoiced_percent = self.env['maintenance.project'].get_invoiced_percent(project.id, self.product_id.id, intervention.maint_type.id)
            self.project_percent_invoiced = invoiced_percent

    
    project_percent_invoiced=fields.Float(compute=get_project_percent_invoiced, string='Amount invoiced') 