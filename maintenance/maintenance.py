'''
Created on 11 juil. 2012

@author: cth
'''
#from osv import osv, fields
from openerp import models,fields
import re
import time
from openerp.tools.translate import _
from datetime import datetime, timedelta
#import netsvc
from openerp import api

def get_datetime(date_field):
    return datetime.strptime(date_field[:19], '%Y-%m-%d %H:%M:%S')

class res_partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    maintenance_installations = fields.One2many('maintenance.installation', 'partner_id', string='Maintenance installations')
    
res_partner()

class maintenance_installation(models.Model):
    _name = 'maintenance.installation'
    _order = 'name'
    
    code = fields.Char("Code", size=255, select=True)
    name = fields.Char("Identification", size=255, select=True)
    partner_id = fields.Many2one('res.partner', string='Customer', select=True)
    address_id = fields.Many2one('res.partner.address', string='Address', select=True)
    invoice_address_id = fields.Many2one('res.partner.address', string='Invoice address', select=True)
    contact_address_id = fields.Many2one('res.partner.address', string='Contact address', select=True)
    elements = fields.One2many('maintenance.element', 'installation_id', "Elements")
    interventions = fields.One2many('maintenance.intervention', 'installation_id', "Interventions", domain=[('state','=','done')]) 
    usability_degree = fields.Char(string="Usability degree", size=255) 
    shop_id = fields.Many2one('sale.shop', 'Shop') 
    active = fields.Boolean("Active")
    state = fields.Selection([('active', 'Active'), ('inactive','Inactive')], string="State", readonly=True)
    
    _defaults = {  
        'code': lambda obj: self.pool.get('ir.sequence').get('maintenance.installation'),
        'active':True  
        }
    
    @api.one
    def installation_draft(self):
        self.state = 'draft'
    
    @api.one
    def installation_active(self, cr, uid, ids):
        self.state='active'
    
    @api.one
    def installation_inactive(self):
        self.state='inactive'
        
    def name_search(self,name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if name:
            addresses = self.env["res.partner.address"].search(['|','|',('name',operator,name),('zip',operator,name),('city',operator,name)])
            partners = self.env["res.partner"].search(['|',('ref',operator,name),('name',operator,name)])
            installations = self.en["maintenance.installation"].search(['|',('code',operator,name),('name',operator,name)], context=context)
            ids = self.search(['|','|','|',('id','in',installations.mapped('id')),('address_id', 'in', addresses.mapped('id')),('contact_address_id','in',addresses.mapped('id')),('partner_id','in',partners.mapped('id'))]+ args, limit=limit)
        else:
            return super(maintenance_installation, self).name_search(name, args, operator, limit)
        
        return ids.name_get()
    
    
    def search(self, args, offset=0, limit=None, order=None, context=None, count=False):
        res = super(maintenance_installation, self).search(args, offset, limit, order, count)
        return res
    
    @api.one
    def name_get(self):
        
        res = []
        
        name = ""
        if self.address_id and self.address_id.name:
            name = name + "["+self.address_id.name+"] "
        elif self.partner_id and self.partner_id.name:
            name = name + "["+self.partner_id.name+"] "
        if self.name:
            name = name + self.name
        res.append((self.id,name))
        return res
    
    @api.onchange('partner_id')
    def on_change_partner_id(self):
        
        if partner_id:
            addr = self.env['res.partner'].address_get(self.partner_id,['invoice', 'delivery', 'contact'])
            self.address_id = addr['delivery']
            self.invoice_address_id = addr['invoice']
    
maintenance_installation()

class intervention_type(models.Model):
    _name="maintenance.intervention.type"
    
    name = fields.Char("Name", size=255, translate=True, required=True)
    color = fields.Selection([('black','Black'), ('red','Red'),('yellow', 'Yellow')], string='Color', required=True)
    workforce_product_id = fields.Many2one('product.product', string="Workforce product", required=True)
    workforce_product_duration = fields.Float(string="Workforce product duration", required=True)
    
intervention_type()

class maintenance_intervention(models.Model):
    _name = 'maintenance.intervention'
    
    def copy(self,default=None):
        new_intervention = super(maintenance_intervention, self).copy(default)
        new_code = self.env['ir.sequence'].get('maintenance.intervention')
        new_intervention.code = new_code
        return new_intervention
    
    @api.one
    def name_get(self):
        result = []
        if self.name:
                result.append((self.id, self.code+' - '+self.name))
        else:
            result.append((self.id, self.code))
        
        return result
    
    
    def _get_intervention_from_task(self, cr, uid, ids, context):
        return [task.intervention_id.id for task in self.pool.get("maintenance.intervention.task").browse(cr, uid, ids, context)]
    
    def _get_task_fields(self, cr, uid, ids, field_names, args, context=None):
        result = {}
        
        for intervention in self.browse(cr, uid, ids, context):
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
                    
                if ('date_start' in field_names) or ('task_month' in field_names):
                    if (date_start == None and task.date_start) or (task.date_start and task.date_start < date_start):
                        date_start = task.date_start
                        
                if 'date_end' in field_names:
                    if (date_end == None and task.date_end) or (task.date_end and task.date_end > date_end):
                        date_end = task.date_end                                    
                
            if intervention.tasks:
                task = intervention.tasks[0]                
                
            if 'task_hours' in field_names:
                result[intervention.id]['task_hours'] = total_hours
            
            if 'task_month' in field_names:
                if date_start:
                    try:
                        result[intervention.id]['task_month'] = int(datetime.strptime(date_start,'%Y-%m-%d %H:%M:%S').strftime('%m'))
                    except:
                        result[intervention.id]['task_month'] = 0                        
                else:
                    result[intervention.id]['task_month'] = 0
                    
            if 'technicians' in field_names:
                result[intervention.id]['technicians'] = tech[0:len(tech)-2]
            
            if 'date_start' in field_names:
                result[intervention.id]['date_start'] = date_start                        
            
            if 'date_end' in field_names:
                result[intervention.id]['date_end'] = date_start
                
            result[intervention.id]['to_plan'] = False
            
            if 'to_plan' in field_names:
                if not planned and to_plan and intervention.state != 'done':
                    result[intervention.id]['to_plan'] = True
                else:
                    result[intervention.id]['to_plan'] = False
            
            if 'task_state' in field_names:
                if planned:
                    result[intervention.id]['task_state'] = 'planned'
                else: 
                    result[intervention.id]['task_state'] = 'to_plan'
                
        return result
    
    code = fields.Char("Code", size=255, select=True, required=True)
    name = fields.Text("Description", select=True)
    #partner_id = fields.Related("installation_id", "partner_id", type="many2one", relation="res.partner", readonly=True, string="Customer", store=True)
    partner_id = fields.Many2one("res.partner",string="Customer",related="installation_id.partner_id",store=True)
    address_id = fields.Many2one("res.partner",string="Adress",related="installation_id.address_id",store=True)
    installation_id = fields.Many2one('maintenance.installation', string='Installation', required=True) 
    state = fields.Selection([('cancel','Cancel'), ('draft','Draft'), ('confirmed', 'Confirmed'), ('done', 'Done')], string="Intervention State", readonly=True)
    task_state = fields.Selection(compute="_get_task_fields", method=True, type="selection", size=255, readonly=True, string="Task state", store={'maintenance.intervention.task':(_get_intervention_from_task,['user_id','date_start','to_plan'],10)}, multi='task', selection=[('to_plan','To plan'), ('planned', 'Planned')])
    tasks = fields.One2many('maintenance.intervention.task','intervention_id', 'Tasks')  
    int_comment = fields.Text("Internal comment")
    ext_comment = fields.Text("External comment")  
    maint_type = fields.Many2one('maintenance.intervention.type', string='Type', required=True)
    contact_address_id = fields.Many2one('res.partner', string='Contact')
    contact_phone = fields.Char(related="contact_address_id.phone", string="Contact phone")
    technicians = fields.Char(compute="_get_task_fields", method=True, size=255, string="Technician", store={'maintenance.intervention.task':(_get_intervention_from_task,['user_id'],10)}, multi='task')
    to_plan = fields.Boolean(computed="_get_task_fields", method=True, string="To plan", store={'maintenance.intervention.task':(_get_intervention_from_task, ['to_plan'],10)}, multi='task')
    date_start = fields.Datetime(compute="_get_task_fields", method=True, string="Beginning",store={'maintenance.intervention.task':(_get_intervention_from_task, ['date_start'],10)}, multi='task')
    date_end = fields.Datetime(compute="_get_task_fields", method=True, string="Beginning",store={'maintenance.intervention.task':(_get_intervention_from_task, ['date_end'],10)}, multi='task')
    task_hours = fields.Float(compute="_get_task_fields", method=True,  size=255, string="Task hours", store={'maintenance.intervention.task':(_get_intervention_from_task,['user_id'],10)}, multi='task')
    task_month = fields.Integer(compute="_get_task_fields", method=True, size=255, string="Task month", store={'maintenance.intervention.task':(_get_intervention_from_task,['user_id'],10)}, multi='task')
    time_planned = fields.Float('Time planned', help='Time initially planned to do intervention.')
    
    _defaults = {  
        'code': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'maintenance.intervention'),
        'task_state':'to_plan',
        'state':'draft',
    }
    
    _order = 'date_start,id desc'
    
    @api.onchange('installation_id')
    def on_change_installation_id(self):        
        if self.installation_id:
            self.partner_id = self.installation_id.partner_id.id
            self.contact_address_id = self.installation_id.contact_address_id.id
            
    @api.one
    def action_cancel(self):
        self.state = 'cancel'
    
    @api.one
    def action_done(self):
        self.state = 'done'
    
    @api.one
    def action_confirm(self):    
        self.state = 'confirmed'
        
        '''  
        logger = netsvc.Logger()
          
        project_pool = self.pool.get("project.project")
        
        interventions = self.browse(cr, uid, ids, context)
        
        updt_vals = {'state': 'confirmed'}
        
        
        i = 0
        total = len(interventions)
        for interv in interventions:
            i = i + 1 
            logger.notifyChannel('Import maintenance intervention (action_confirm)', netsvc.LOG_INFO, 'interv = '+str(interv.id)+" -- "+str(i)+"/"+str(total))
           
            #update intervention
            try:
                self.write(cr, uid, [interv.id], updt_vals, context=context)
            except:
                ''
        return True
        '''

maintenance_intervention()

class maintenance_element(models.Model):
    _name = 'maintenance.element'
    _order = 'name'
    
    def copy(self, cr, uid, id, default=None, context=None):
        new_id = super(maintenance_element, self).copy(cr, uid, id, default, context)
        new_code = self.pool.get('ir.sequence').get(cr, uid, 'maintenance.element')
        self.write(cr, uid, [new_id], {'code':new_code}, context=context)
        return new_id
    
    @api.one
    def name_get(self):
        
        result = []
        if self.serial_number:
            result.append((self.id, self.name+' - ['+self.serial_number+']'))
        else:
            result.append((self.id, self.name))
        return result
    
    #add search on code
    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        res = super(maintenance_element, self).name_search(cr, user, name, args, operator, context, limit)
        if res:
            return res
        else:
            if not args:
                args = []
            args.append(('code',operator,name))
            res_ids = self.search(cr, user, args, limit=limit)
            result = self.name_get(cr, user, res_ids, context=context)
        return result
    
    installation_id = fields.Many2one('maintenance.installation', 'Installation', select=True)
    code = fields.Char("Code", size=255, select=True)
    partner_id = fields.Many2one("res.partner",related="installation_id.partner_id", readonly=True, string="Customer", store=True)
    name = fields.Char("Name", size=255, select=True) 
    product_id = fields.Many2one('product.product', 'Product', select=True)
    serial_number = fields.Char("Serial Number", size=255, select=True) 
    description = fields.Text("Description")
    installation_date = fields.Date("Installation date") 
    warranty_date = fields.Date("Warranty date") 
    location = fields.Char("Location", size=255) 
    suivi_tmi = fields.Text("Suivi TMI")
    piece_tmi = fields.Text("Piece TMI", readonly=True)        
    address_id = fields.Many2one("res.partner", related="installation_id.address_id", readonly=True, string="Address")
    serialnumber_required = fields.Boolean("Serial number required")
    visible_for_intervention = fields.Boolean("Visible for interventions")
    active = fields.Boolean("Active")
    shop_id = fields.Many2one('sale.shop',related='installation_id.shop_id', string="Shop")
    
    _defaults = {
        'code': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'maintenance.element'),
        'visible_for_intervention':True, 
        'active':True
    }
maintenance_element()

class maintenance_intervention_task(models.Model):
    _name = 'maintenance.intervention.task'
    
    def _get_to_plan(self, cr, uid, ids, field_names, args, context=None):
        res = {}
        for task in self.browse(cr, uid, ids, context):
            res[task.id] = not bool(task.user_id and task.date_start)
        return res
    
    def _get_maintenance_time(self, cr, uid, ids, field_names, args, context=None):
        res = {}
        for task in self.browse(cr, uid, ids, context):
            workforce_product_duration = 0.25
            if task.intervention_id and task.intervention_id.maint_type and task.intervention_id.maint_type.workforce_product_duration:
                workforce_product_duration = task.intervention_id.maint_type.workforce_product_duration
            maintenance_time = int(task.planned_hours // workforce_product_duration)
            if task.planned_hours % task.intervention_id.maint_type.workforce_product_duration > 0: #all period began should be paid
                maintenance_time = maintenance_time + 1
            res[task.id] = maintenance_time
        return res
    
    intervention_id = fields.Many2one("maintenance.intervention", "Intervention")
    name = fields.Char('Task Summary', size=128)
    user_id = fields.Many2one('res.users', 'Assigned to')
    date_start = fields.Datetime('Starting Date',select=True)
    date_end = fields.Datetime('Ending Date',select=True)
    planned_hours = fields.Float('Planned Hours', help='Estimated time to do the task, usually set by the project manager when the task is in draft state.')
    to_plan = fields.Boolean(compute="_get_to_plan", string='To plan', method=True, store={'maintenance.intervention.task':(lambda self, cr, uid, ids, c={}: ids, ['date_start','user_id'],10)}) 
    break_time = fields.Float("Break time")
    maintenance_time = fields.Integer(compute="_get_maintenance_time", string='Maintenance time', method=True, store={'maintenance.intervention.task':(lambda self, cr, uid, ids, c={}: ids, ['planned_hours'],10)}, help="Number of maintenance time period to fill duration of intervention")
    
    _defaults = {  
        'to_plan': True,  
    }
    
    @api.one
    def write(self, vals):
        if 'state' in vals and 'date_end' in vals and 'date_start' not in vals and vals['state'] == 'cancelled':
            vals['date_start'] = vals['date_end']
        
        result = super(maintenance_intervention_task,self).write(vals)
        return result    
    
    @api.onchange('date_end')
    def on_change_date_end(self):  
        if self.date_start and self.date_end:
            delta = get_datetime(self.date_end) - get_datetime(self.date_start) - timedelta(hours=self.break_time)
            self.planned_hours = delta.seconds/3600.
  
maintenance_intervention_task()

