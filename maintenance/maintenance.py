from openerp import models, fields, api
import re
import time
from datetime import datetime, timedelta
from openerp import netsvc

def get_datetime(date_field):
    return datetime.strptime(date_field[:19], '%Y-%m-%d %H:%M:%S')

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    maintenance_installations = fields.One2many('maintenance.installation', 'partner_id', string='Maintenance installations',help="The Installations for Maintenance related to this partner")


class maintenance_installation(models.Model):
    _name = 'maintenance.installation'
    _order = 'name'
    _inherit=['mail.thread']
    
    @api.multi
    def _get_last_interventions(self):
        res = {}
        
        for installation in self:
            installation.last_interventions = self.env['maintenance.intervention'].search([("installation_id",'=',installation.id),("state","=","done")], limit=2, order='date_start desc').mapped('id')
            
        return res
    
    code = fields.Char("Code", size=255, select=True,help="The Maintenance Installation Code",default=lambda obj: obj.env['ir.sequence'].get('maintenance.installation'))
    name = fields.Char("Identification", size=255)
    partner_id = fields.Many2one('res.partner', string='Customer',help="The partner linked to this maintenance installation")
    address_id = fields.Many2one('res.partner', string='Address', help="The address where the installation is located")
    invoice_address_id = fields.Many2one('res.partner', string='Invoice address',domain=[('type','=','invoice')])
    contact_address_id = fields.Many2one('res.partner', string='Contact address', domain=[('type','=','contact')],help="The contact for this installation")
    elements = fields.One2many('maintenance.element', 'installation_id', "Elements",help="The elements contained in this installation")
    interventions = fields.One2many('maintenance.intervention', 'installation_id', "Interventions", help="The interventions linked to this installation")
    last_interventions = fields.One2many(compute=_get_last_interventions, string="Last interventions", comodel_name="maintenance.intervention", method=True)
    #usability_degree = fields.Char(string="Usability degree", size=255, ), 
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse',help="The Warehouse linked to this Installation")
    #active = fields.Boolean("Active",help="If this installation is active or not") 
    state = fields.Selection([('active', 'Active'), ('inactive','Inactive')], string="State", readonly=True,help="The installation can take two states<br/> -active <br/> -inactive")
    
    @api.multi
    def installation_active(self):
        for installation in self:
            installation.state = 'active'
        return True
    
    @api.multi
    def installation_inactive(self):
        for installation in self:
            installation.state = 'inactive'
        return True
    
    @api.model
    def name_search(self,name='', args=None, operator='ilike', limit=100):
        if not args:
            args = []
        if name:
            addresses = self.env['res.partner'].search(['|','|',('name',operator,name),('zip',operator,name),('city',operator,name)])
            partners = self.env['res.partner'].search(['|',('ref',operator,name),('name',operator,name)])
            installations = self.env['maintenance.installation'].search(['|',('code',operator,name),('name',operator,name)])
            ids = self.search(['|','|','|',('id','in',installations.mapped('id')),('address_id', 'in', addresses.mapped('id')),('contact_address_id','in',addresses.mapped('id')),('partner_id','in',partners.mapped('id'))]+ args, limit=limit)
        else:
            return super(maintenance_installation, self).name_search(name, args, operator, limit)
        
        return ids.name_get()
    
    '''
    def search(self,*args,**kwargs):
        res = super(maintenance_installation, self).search(*args,**kwargs)
        return res
    '''
    
    @api.multi
    def name_get(self):
        res = []
        for record in self:
            name_tab = []
            if record.name:
                name_tab.append(record.name)
            if record.partner_id and record.partner_id.name:
                name_tab.append(record.partner_id.name)
            if record.address_id and record.address_id.city:
                name_tab.append(record.address_id.city)
            if record.code:
                name_tab.append('('+record.code+')')
            try:
                res.append((record.id,' - '.join(name_tab)))
            except:
                ''
        return res
    
    @api.onchange('partner_id')
    def on_change_partner_id(self, invoice_address_id, address_id):
        
        result = {}
        
        if self.partner_id:
            addr = self.env['res.partner'].address_get([self.partner_id.id], ['invoice', 'delivery', 'contact'])
            result['invoice_address_id'] = addr['invoice']
            result['address_id'] = addr['delivery']
            #result['contact_address_id'] = addr['contact']
        return {'value': result}

class intervention_type(models.Model):
    _name="maintenance.intervention.type"
    
    name = fields.Char("Name", size=255, translate=True, required=True)
    workforce_product_id = fields.Many2one('product.product', string="Workforce product", required=True,help="Default workforce product for this kind of intervention")
    workforce_product_duration = fields.Float(string="Workforce product duration", required=True,help="Unit of time for workforce product")
    
class maintenance_intervention(models.Model):
    _name = 'maintenance.intervention'
    
    _inherit = ['mail.thread','ir.needaction_mixin']
    
    @api.multi
    def print_intervention(self):
        '''
        This function prints the maintenance intervention
        '''
        assert len(self) == 1, 'This option should only be used for a single id at a time'
        
        return self.env['report'].get_action(self,'maintenance.report_maintenance_intervention')
    
    @api.model
    def _needaction_domain_get(self):
        return ['&',('tasks.user_id','=', self.env.uid),('state','=', 'confirmed')]
    
    @api.one
    def copy(self,default=None):
        new_id = super(maintenance_intervention, self).copy(default)
        new_code = self.env['ir.sequence'].get('maintenance.intervention')
        new_id.code = new_code
        return new_id
    
    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        result = []
        for me in self.browse(cr, uid, ids, context=context):
            if me.name:
                result.append((me.id, me.code+' - '+me.name))
            else:
                result.append((me.id, me.code))
        return result
    
    
    '''
    def _get_intervention_from_task(self):
        return [task.intervention_id.id for task in self.env['maintenance.intervention.task'].browse(cr, uid, ids, context)]
    
    '''
    @api.one
    @api.depends('tasks.user_id','date_start','to_plan','date_end')
    def _get_task_fields(self):
        result = {}
        
        for intervention in self:
            tech = ""
            to_plan = False
            planned = False
            date_end = None
            date_start = None
            result[intervention.id] = {}
            
            if intervention.tasks:
                planned = True
            
            total_hours = 0.
                
            for task in intervention.tasks:
                if task.planned_hours:
                    total_hours = total_hours + task.planned_hours
                
                if task.user_id and task.user_id.name not in tech:
                    tech += task.user_id.name+", "
                if not to_plan:
                    to_plan = task.to_plan
                if planned and not task.date_start or not task.user_id:
                    planned = False
                    
                if (date_start == None and task.date_start) or (task.date_start and task.date_start < date_start):
                    date_start = task.date_start
                        
                
                if (date_end == None and task.date_end) or (task.date_end and task.date_end > date_end):
                    date_end = task.date_end                                    
                
            if intervention.tasks:
                task = intervention.tasks[0]                

            intervention.task_hours = total_hours
            
            
            if date_start:
                try:
                    intervention.task_month=int(datetime.strptime(date_start,'%Y-%m-%d %H:%M:%S').strftime('%m'))
                except:
                    intervention.task_month = 0               
            else:
                intervention.task_month = 0
                    
            intervention.technicians = tech[0:len(tech)-2]
            
            intervention.date_start = date_start                        
            
            intervention.date_end = date_end
                
            intervention.to_plan = False
            
            if not planned and to_plan and intervention.state != 'done':
                intervention.to_plan = True
            else:
                intervention.to_plan = False
            
            
            if planned:
                intervention.task_state = 'planned'
            else: 
                intervention.task_state = 'to_plan'
                    
    @api.multi
    def _get_code(self):
        return self.env['ir.sequence'].get('maintenance.intervention')
    
    code = fields.Char("Code", size=255, select=True, required=True,default=_get_code)
    name = fields.Text("Description", select=True)
    partner_id = fields.Many2one("res.partner", type="many2one", related='installation_id.partner_id', readonly=True, string="Customer", store=True,help="Customer linked to the installation")
    address_id = fields.Many2one("res.partner",related="installation_id.address_id", readonly=True, string="Address", store=True,help="Address of the installation")
    installation_id = fields.Many2one('maintenance.installation', string='Installation', required=True) 
    state = fields.Selection([('cancel','Cancel'), ('draft','Draft'), ('confirmed', 'Confirmed'), ('done', 'Done')], string="Intervention State", readonly=True,default='draft',track_visibility='onchange')
    task_state = fields.Selection(compute='_get_task_fields', size=255,default='to_plan', readonly=True, string="Task state", selection=[('to_plan','To plan'), ('planned', 'Planned')])
    tasks = fields.One2many('maintenance.intervention.task','intervention_id', 'Tasks')
    int_comment = fields.Text("Internal comment")
    ext_comment = fields.Text("External comment") 
    maint_type = fields.Many2one('maintenance.intervention.type', string='Type', required=True)
    contact_address_id = fields.Many2one('res.partner', string='Contact')
    contact_phone = fields.Char(relation="res.partner",related="contact_address_id.phone", string="Contact phone")
    technicians = fields.Char(compute='_get_task_fields', size=255, string="Technician",store=True)
    to_plan = fields.Boolean(compute='_get_task_fields', string="To plan",store=True)
    date_start = fields.Datetime(compute='_get_task_fields', string="Beginning", store=True)
    date_end = fields.Datetime(compute='_get_task_fields',  string="End",store=True)
    task_hours = fields.Float(compute='_get_task_fields', size=255, string="Task hours",store=True)
    task_month = fields.Integer(compute='_get_task_fields', size=255, string="Task month",store=True)
    time_planned = fields.Float('Time planned', help='Time initially planned to do intervention.')
    
    
    _order = 'id desc'
    
    @api.onchange('installation_id')
    def on_change_installation_id(self):        
        if self.installation_id:
            self.partner_id=self.installation_id.id
            self.contact_address_id = self.installation_id.contact_address_id.id
    
    @api.one
    def action_cancel(self):
        self.state = 'cancel'        
        return True
    
    @api.one
    def action_done(self):
        self.state = 'done'
        return True
    
    @api.one
    def action_confirm(self):
        self.state = 'confirmed'
        return True


class maintenance_element(models.Model):
    _name = 'maintenance.element'
    _order = 'name'
    
    @api.one
    def copy(self,default=None):
        new_element = super(maintenance_element, self).copy(default)
        new_element.code = self.env['ir.sequence'].get('maintenance.element')
    
    @api.multi
    def name_get(self):
        result = []
        for element in self:
            if element.serial_number:
                result.append((element.id, element.code + ' - ' +element.name+' - ['+element.serial_number+']'))
            else:
                result.append((element.id, element.code + ' - ' +element.name))
        return result
    
    #add search on code
    def name_search(self,name='', args=None, operator='ilike', limit=100):
        res = super(maintenance_element, self).name_search(name, args, operator, limit)
        if res:
            return res
        else:
            if not args:
                args = []
            args.append(('code',operator,name))
            elements = self.search(args, limit=limit)
            result = elements.name_get()
        return result
    
    @api.multi
    def _get_code(self):
        return self.env['ir.sequence'].get('maintenance.element')
    
    installation_id = fields.Many2one('maintenance.installation', 'Installation', select=True)
    code = fields.Char("Code", size=255, select=True,default=_get_code)
    partner_id = fields.Many2one(related="installation_id.partner_id", relation="res.partner", readonly=True, string="Customer", store=True)
    name = fields.Char("Name", size=255, select=True) 
    product_id = fields.Many2one('product.product', 'Product', select=True)
    serial_number = fields.Char("Serial Number", size=255, select=True)
    description = fields.Text("Description")
    installation_date = fields.Date("Installation date")
    warranty_date = fields.Date("Warranty date")
    location = fields.Char("Location", size=255)
    #A METTRE DANS ELNEO_MAINTENANCE
    #'suivi_tmi':fields.text("Suivi TMI"), 
    #'piece_tmi':fields.text("Piece TMI", readonly=True),        
    address_id = fields.Many2one(related="installation_id.address_id", relation="res.partner", readonly=True, string="Installation Address")
    serialnumber_required = fields.Boolean("Serial number required")
    visible_for_intervention = fields.Boolean("Visible for interventions",default=True)
    active = fields.Boolean("Active",default=True)
    warehouse_id = fields.Many2one(related='installation_id.warehouse_id', relation='sale.shop', string="Warehouse")

class maintenance_intervention_task(models.Model):
    _name = 'maintenance.intervention.task'
    
    inherit = ['ir.needaction_mixin']
    
    @api.one
    @api.depends('user_id','date_start')
    def _get_to_plan(self):
        self.to_plan = not bool(self.user_id and self.date_start)
    
    @api.one
    @api.depends('planned_hours')
    def _get_maintenance_time(self):
        workforce_product_duration = 0.25
        if self.intervention_id and self.intervention_id.maint_type and self.intervention_id.maint_type.workforce_product_duration:
            workforce_product_duration = self.intervention_id.maint_type.workforce_product_duration
        maintenance_time = int(self.planned_hours // workforce_product_duration)
        if self.planned_hours % self.intervention_id.maint_type.workforce_product_duration > 0: #all period began should be paid
            maintenance_time = maintenance_time + 1
        self.maintenance_time = maintenance_time
    
    
    intervention_id = fields.Many2one("maintenance.intervention", "Intervention")
    name = fields.Char('Task Summary', size=128)
    user_id = fields.Many2one('res.users', 'Assigned to')
    date_start = fields.Datetime('Starting Date',select=True)
    date_end = fields.Datetime('Ending Date',select=True)
    planned_hours = fields.Float('Planned Hours', help='Estimated time to do the task, usually set by the project manager when the task is in draft state.')
    to_plan = fields.Boolean(compute=_get_to_plan, string='To plan', method=True, default=True,track_visibility='onchange',store=True)
    break_time = fields.Float("Break time")
    maintenance_time = fields.Integer(compute=_get_maintenance_time, string='Maintenance time', method=True, help="Number of maintenance time period to fill duration of intervention")
    
    @api.one
    def write(self,vals):
        if 'state' in vals and 'date_end' in vals and 'date_start' not in vals and vals['state'] == 'cancelled':
            vals['date_start'] = vals['date_end']
        
        return super(maintenance_intervention_task,self).write(vals)    
    
    @api.onchange('date_end','break_time','date_start')
    def on_change_date_end(self):  
        if self.date_start and self.date_end:
            delta = get_datetime(self.date_end) - get_datetime(self.date_start) - timedelta(hours=self.break_time)
            self.planned_hours = delta.seconds/3600.
     
    @api.model        
    def _needaction_domain_get(self):
        return ['&', ('to_plan', '=', True),('user_id','=',self.user.id)]