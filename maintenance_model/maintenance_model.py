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

from datetime import datetime, timedelta
import calendar
import math

from openerp import models, fields, api, _
from openerp.exceptions import Warning

def add_months(sourcedate,months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month / 12
    month = month % 12 + 1
    day = min(sourcedate.day,calendar.monthrange(year,month)[1])
    return datetime(year=year,month=month,day=day)


class maintenance_element_model(models.Model):
    _name = "maintenance.element.model"
    
    @api.one
    def update_interventions(self):
        """
        If model has changed, update linked draft interventions
        """
        res = True
        
        # Add
    
        # Looking for interventions with products related to model (maybe several)
        generation_details = self.env['maintenance.generation.detail'].search([('intervention_model_id','in',self.intervention_model_ids.mapped('id'))])
        
        interventions = self.env['maintenance.intervention'].search([('state','=','draft'),('id','in',generation_details.mapped('intervention_id.id'))])
        
        for intervention in interventions:
            
            generation_details = self.env['maintenance.generation.detail'].search([('intervention_id','=',intervention.id)])
            
            unique_models = generation_details.mapped('intervention_model_id')
            
            # For a particular intervention, we take all maintenance elements concerned by change
            for intervention_model in unique_models:
                
                # Delete intervention product and build the intervention products list
                products_to_unlink = intervention.intervention_products.filtered(lambda r:r.intervention_product_model not in intervention_model.intervention_product_model_ids and r.intervention_model.id == intervention_model.id)
                
                intervention_products = intervention.intervention_products - products_to_unlink 
                
                products_to_unlink.unlink()
                
                for product_model in intervention_model.intervention_product_model_ids:
                    
                    # Product Modification
                    self._update_products(intervention_products, product_model)
                    
                    
                    # ADD - A product (from model) is not in the current intervention product list
                    if (product_model.product_id not in intervention_products.mapped('product_id')):
                        value = {
                                 'intervention_product_model':product_model.id,
                                 'intervention_model':intervention.intervention_model_id.id,
                                 'quantity':product_model.quantity,
                                 'product_id':product_model.product_id.id,
                                 'intervention_id':intervention.id,
                                 'description':product_model.product_id.name_get()[0][1], 
                                 'maintenance_element_id':generation_details[0].maintenance_element_id.id, 
                                 'sale_price':product_model.product_id.list_price,
                                 'cost_price':product_model.product_id.cost_price,
                                 'discount':False,
                                 'delay':product_model.product_id.sale_delay,
                                 'type':False,
                                 }
                        self.env['maintenance.intervention.product'].create(value)
     
        return res
    
    #Update products which have different quantities
    @api.model
    def _update_products(self,intervention_products,product_model):
        for product in intervention_products.filtered(lambda r:r.intervention_product_model and r.intervention_product_model.id == product_model.id and r.quantity !=product_model.quantity):
            product.quantity = product_model.quantity
            
        return True       
    
    '''
    def get_max_period_timeofuse(self, cr, uid, ids, context=None):
        intervention_model_pool = self.pool.get('maintenance.intervention.model')
        result = {}
        for model_id in ids:
            element_ids = intervention_model_pool.search(cr, uid, [('element_model_id','=',model_id)], order="period_timeofuse desc", limit=1, context=context)
            if element_ids:
                result[model_id] = intervention_model_pool.browse(cr, uid, element_ids[0], context).period_timeofuse
        return result
    '''
    
    '''
    def get_max_period_months(self, cr, uid, ids, context=None):
        intervention_model_pool = self.pool.get('maintenance.intervention.model')
        result = {}
        for model_id in ids:
            element_ids = intervention_model_pool.search(cr, uid, [('element_model_id','=',model_id)], order="period_months desc", limit=1, context=context)
            if element_ids:
                result[model_id] = intervention_model_pool.browse(cr, uid, element_ids[0], context).period_months
        return result
    '''
    
    @api.model
    def search(self,args, offset=0, limit=None, order=None, count=False):
        for arg in args:
            if arg[0] == 'product_ids':
                self.env.cr.execute("select distinct maintenance_element_model.id from maintenance_element_model left join maintenance_element_model_product_rel left join product_product on product_product.id = maintenance_element_model_product_rel.product_id on maintenance_element_model_product_rel.model_id = maintenance_element_model.id where product_product.default_code ilike '%%%s%%' or name ilike '%%%s%%'"%(arg[2],arg[2]))
                model_ids = [t[0] for t in self.env.cr.fetchall()]
                args.append(('id','in',model_ids))
                args.remove(arg)
            
        return super(maintenance_element_model, self).search(args, offset=offset, limit=limit, order=order, count=count)
    
    
    name=fields.Char(string="Name", size=255)
    description=fields.Text("Description")
    product_ids=fields.Many2many('product.product', 'maintenance_element_model_product_rel', 'model_id', 'product_id', string="Concerned products")
    intervention_model_ids=fields.One2many('maintenance.intervention.model', 'element_model_id', string="Intervention plan")
    serial_number_from=fields.Char(size=255, string="From serial number")
    serial_number_to=fields.Char(size=255, string="To serial number")
    time_counter=fields.Boolean("Time counter", help="Check if this type of element has time counter.")


class maintenance_intervention_model(models.Model):
    _name = 'maintenance.intervention.model'
    
    element_model_id=fields.Many2one('maintenance.element.model', "Element model")                 
    name=fields.Char(string="Name", size=255)
    intervention_type_id=fields.Many2one("maintenance.intervention.type", "Type of intervention", required=True) 
    description=fields.Text("Description")
    hours_cycle=fields.Integer("Number of operating hours between two intervention") 
    hours_first=fields.Integer("Number of operating hours before first intervention")
    months_cycle=fields.Integer("Number of months between two interventions")
    months_first=fields.Integer("Number of months before first intervention")
    duration=fields.Float("Duration of intervention")
    intervention_product_model_ids=fields.One2many("maintenance.intervention.product.model", "intervention_model_id", string="Products")
    no_generation_of_intervention=fields.Boolean('Non-contracted')

class maintenance_intervention_product_model(models.Model):
    _name="maintenance.intervention.product.model"
    
    _rec_name = 'product_id' 
    
    intervention_model_id=fields.Many2one("maintenance.intervention.model", string="Intervention model") 
    product_id=fields.Many2one("product.product", string="Product")
    quantity=fields.Float('Quantity',default=1)
      
class product_product(models.Model):
    _inherit = 'product.product' 

    maintenance_element_model_ids=fields.Many2many('maintenance.element.model', 'maintenance_element_model_product_rel', 'product_id', 'model_id', string="Concerned intervention models")
    

class maintenance_element(models.Model):
    _inherit = 'maintenance.element' 
    
    intervention_generation_start_hours=fields.Float('Counter at beginning of generation', help="When we do generation of interventions from project, we consider this value as beginning counter.") 
    intervention_generation_first_date=fields.Date('Date of first intervention (auto. generation)', help="When we do generation of interventions from project, we consider this value as first intervention date. This date is not used if start hours are filled.")
    element_model_id=fields.Many2one('maintenance.element.model', 'Element model')
    main_element=fields.Boolean("Main element", help="If other elements of the project do not have expected time of use, we use expected time of use of main element")
    current_project_start_date = fields.Date(related='current_project_id.used_intervention_generation_start_date',string='Intervention beginning',readonly=True)
    
    @api.onchange('timeofuse_history')
    def on_change_timeofuse_history(self):
        reference_times = self.timeofuse_history.sorted(key=lambda r:r.date,reverse=True)
        if(len(reference_times) > 0):
            reference_time = reference_times[0]
        if (not self.intervention_generation_first_date):
            return
        start_date = datetime.strptime(self.intervention_generation_first_date,"%Y-%m-%d")
        
        self.intervention_generation_start_hours = self.compute_start_hour(reference_time, start_date, self.expected_time_of_use)
    
    @api.model
    def compute_start_hour(self,reference_time,start_date,expected_time_of_use):
        '''
        We calculate the estimated counter start time
        '''
        
        if (not reference_time or not reference_time.time_of_use):
            return 0
        
        # We can't calculate the start hour if there is no date for the reference counter
        if (not reference_time.date or not start_date):
            return reference_time.time_of_use
        
        final_hour = reference_time.time_of_use
        delta = (start_date - datetime.strptime(reference_time.date,"%Y-%m-%d %H:%M:%S")).days
        
        if (delta and delta >= 0):
            hours_diff = (expected_time_of_use / 365.) * delta
            final_hour = reference_time.time_of_use + hours_diff
            
        return final_hour
        
        
    
    # Function to calculate (and estimate) the maintenance element counter at
    # the begining of the project intervention generation date
    @api.one
    def calculate_start_hour(self):
        project = self._find_project()
        
        if project and project.intervention_generation_start_date:
            
            reference_times = self.timeofuse_history.sorted(key=lambda r:r.date,reverse=True)
            if(len(reference_times) > 0):
                reference_time = reference_times[0]
            
            self.intervention_generation_start_hours = self.compute_start_hour(reference_time,datetime.strptime(project.intervention_generation_start_date,"%Y-%m-%d"),self.expected_time_of_use)
            

    
    # As a maintenance element cannot be linked to one and only
    # one project, we estimate the project on which calculate
    def _find_project(self):
        
        for project in self.maintenance_projects.filtered(lambda r:r.state in ('active','draft')).sorted(key=lambda x:x,reverse=True):
            return project
        
    
    @api.multi
    def get_interventions(self,project):
        
        #date_from = project.intervention_generation_start_date or project.date_start
        date_from = project.used_intervention_generation_start_date
        date_to = project.date_end
        
        result = []
       
        begin = datetime.strptime(date_from, '%Y-%m-%d')
        
        if date_to:
            end = datetime.strptime(date_to, '%Y-%m-%d')
        else:
            #TODO: Put a config parameter to not store it in the code
            end = begin + timedelta(days=365*2)
        
        diff = end-begin
        days = diff.days

        installation = project.installation_id
        
        merge_table = {}
        for element in self:
            if element.element_model_id:
                for intervention_model in element.element_model_id.intervention_model_ids:
                    if intervention_model.no_generation_of_intervention:
                        continue
                    
                    if not intervention_model.months_first and not  intervention_model.hours_first:
                        raise Warning(_('You have to fill at least months or hours for first intervention for intervention %s of model %s.')%(intervention_model.name, element.element_model_id.name)) 
                
                    if not intervention_model.months_cycle and not  intervention_model.hours_cycle:
                        raise Warning(_('You have to fill at least cycle months or cycle hours for intervention %s of model %s.')%(intervention_model.name, element.element_model_id.name))
                    
                    if not element.expected_time_of_use and (intervention_model.hours_first != 0 or intervention_model.hours_cycle != 0):
                        raise Warning(_('You have to define expected annual time of use of element %s.')%(element.name))
                    
                    #find if element operate enough to compute days from operating time
                    #for first intervention
                    hours_until_max_time_first = (element.expected_time_of_use*intervention_model.months_first)/12
                    if intervention_model.hours_first == 0 or (intervention_model.months_first != 0 and hours_until_max_time_first < intervention_model.hours_first):
                        days_first = intervention_model.months_first*(365./12.)
                        hours_first = element.expected_time_of_use*intervention_model.months_first/12.
                    else:
                        days_first =  ((intervention_model.hours_first*12.)/element.expected_time_of_use)*(365./12)
                        hours_first = intervention_model.hours_first
                    
                    #for next interventions
                    hours_for_max_time = (element.expected_time_of_use*intervention_model.months_cycle)/12.
                    if intervention_model.hours_cycle == 0 or (intervention_model.months_cycle != 0 and hours_for_max_time < intervention_model.hours_cycle):
                        days_cycle = intervention_model.months_cycle*(365./12.)
                        hours_cycle = element.expected_time_of_use*intervention_model.months_cycle/12.
                    else:
                        days_cycle =  ((intervention_model.hours_cycle*12.)/element.expected_time_of_use)*(365./12.)
                        hours_cycle = intervention_model.hours_cycle
                    
                    #existing installation
                    if element.intervention_generation_start_hours and intervention_model.hours_cycle:
                        current_hours = hours_cycle*math.ceil((element.intervention_generation_start_hours-hours_first)/hours_cycle)+hours_first
                        days = (365*(current_hours-element.intervention_generation_start_hours))/element.expected_time_of_use
                        current_date = begin+timedelta(days=days)
                    elif element.intervention_generation_first_date:
                        current_date = datetime.strptime(element.intervention_generation_first_date, '%Y-%m-%d')
                        current_hours = (element.expected_time_of_use*(current_date-begin).days)/365.
                    #case of new installation
                    else:
                        current_date = begin+timedelta(days=days_first)
                        current_hours = hours_first
                                                
                    keep_alive = 0
                    
                    while current_date <= end:
                        
                        if current_date >= begin:
                            keep_alive = keep_alive+1
                            if keep_alive > 1000:
                                raise Warning(_('Technical problem, please call your IT support.'))
                            
                            merge_key = current_date.strftime('%Y-%m-%d')
                        
                            if not merge_table.has_key(merge_key):
                                merge_table[merge_key] = []
                                
                            intervention = {
                                'name':intervention_model.name,
                                'maint_type':intervention_model.intervention_type_id.id,
                                'date_scheduled':current_date, 
                                'date_start':current_date, 
                                'date_end':current_date+timedelta(hours=intervention_model.duration), 
                                'planned_hours':intervention_model.duration, 
                                'description':intervention_model.description, 
                                'installation_id':installation.id,
                                'contact_address_id':installation.contact_address_id.id, 
                                'intervention_products':[(0,0,{'delay':product_intervention_model.product_id.sale_delay,'sale_price':product_intervention_model.product_id.product_tmpl_id.list_price,'cost_price':product_intervention_model.product_id.standard_price,'description':product_intervention_model.product_id.name_get()[0][1],'intervention_model':product_intervention_model.intervention_model_id.id,'intervention_product_model':product_intervention_model.id,'maintenance_element_id':element.id,'product_id':product_intervention_model.product_id.id, 'quantity':product_intervention_model.quantity}) for product_intervention_model in intervention_model.intervention_product_model_ids],
                                'intervention_timeofuse':[(0,0,{'expected_time_of_use':current_hours,'maintenance_element_id':element.id})],
                                'hours':current_hours, 
                                'element_model_id':element.element_model_id.id,
                                'intervention_model_id':intervention_model.id, 
                                'project_id':project.id, 
                                'element_name':element.name
                            }
                            
                            merge_table[merge_key].append(intervention)
                        
                        current_hours = current_hours+hours_cycle
                        current_date = current_date+timedelta(days=days_cycle)
                        
        #merge interventions of the same element for the same date
        for key in merge_table:
            #order interventions in the same date by date
            #merge_table[key] = sorted(merge_table[key], lambda elt:elt['date_start'])
            
            duration = 0
            merged_intervention = {
                'name':'', 
                'description':'', 
                'maint_type':merge_table[key][0]['maint_type'],
                'date_scheduled':merge_table[key][0]['date_scheduled'],
                'date_start':merge_table[key][0]['date_start'],
                'installation_id':merge_table[key][0]['installation_id'],
                'contact_address_id':merge_table[key][0]['contact_address_id'],
                'hours':merge_table[key][0]['hours'],
                'element_model_id':merge_table[key][0]['element_model_id'],
                'project_id':merge_table[key][0]['project_id'],
                'intervention_timeofuse':merge_table[key][0]['intervention_timeofuse'],
                'intervention_products' : [],
                'intervention_detail':[],
            }
            
            element_names = {}
            
            max_hours = 0
            
            for intervention in merge_table[key]:
                #manage element name and hours
                if not element_names.has_key(intervention['element_name']):
                    element_names[intervention['element_name']] = {'name':'','hours':0}
                
                element_names[intervention['element_name']]['name'] = (element_names[intervention['element_name']]['name'] or '')+(intervention['name'] or '')+'+'
                
                if merged_intervention['hours'] > element_names[intervention['element_name']]['hours']:
                    element_names[intervention['element_name']]['hours'] = intervention['hours']
                
                if intervention['hours'] > max_hours:
                    max_hours = intervention['hours']
                
                merged_intervention['name'] = merged_intervention['name'] + (intervention['name'] and intervention['name'] or '') + '+'
                merged_intervention['description'] = merged_intervention['description'] + (intervention['description'] or '') + '\n'
                merged_intervention['intervention_products'] = merged_intervention['intervention_products']+intervention['intervention_products']
                merged_intervention['intervention_detail'].append({'intervention_model_id':intervention['intervention_model_id'], 'maintenance_element_id':element.id})
                duration = duration + intervention['planned_hours']
                
                tou_found=False
                if (merged_intervention['intervention_timeofuse']):
                    for timeofuse in merged_intervention['intervention_timeofuse']:
                        if (timeofuse[2] and timeofuse[2].has_key('maintenance_element_id') and intervention['intervention_timeofuse'][0][2] and intervention['intervention_timeofuse'][0][2].has_key('maintenance_element_id')):
                            if timeofuse[2]['maintenance_element_id'] == intervention['intervention_timeofuse'][0][2]['maintenance_element_id']:
                                tou_found = True
                
                if (not tou_found):
                    merged_intervention['intervention_timeofuse'] += intervention['intervention_timeofuse']
                            
                
            intervention_name = ''
            for element_name in element_names:
                hours = element_names[element_name]['hours']
                intervention_name = intervention_name+element_name+_(': ')+element_names[element_name]['name'][0:-1]+(hours and _(' (at %sh)')%(hours,) or '')+' ; '
            intervention_name = intervention_name[0:-3]
                
            additional_labor_time = 0
            if ('installation_id' in merged_intervention) and merged_intervention['installation_id']:
                additional_labor_time = self.env['maintenance.installation'].browse(merged_intervention['installation_id']).additional_labor_time
            
            #compute duration (keep only one additional time)
            duration = duration+additional_labor_time
            
            merged_intervention['tasks'] = [(0,0,
                {'date_start':merge_table[key][0]['date_start'], 
                 'date_end':merge_table[key][0]['date_start']+timedelta(hours=duration), 
                 'planned_hours':duration})]
            
            merged_intervention['time_planned'] = duration
            merged_intervention['date_end'] = merged_intervention['date_start']+timedelta(hours=duration)
            merged_intervention['name'] = intervention_name
            #merged_intervention['expected_time_of_use'] = max_hours
            merged_intervention['description'] = merged_intervention['description'][0:-2]
            merged_intervention['elements'] = [element.id]
            
            result.append(merged_intervention)
                    
                
        result = sorted(result, key=lambda elt:elt['date_start'], reverse=True)
                
        return result
    
    @api.one
    @api.onchange('product_id')
    def onchange_product_id(self):
        
        if self.product_id:
            models = self.product_id.maintenance_element_model_ids.filtered(lambda r:not self.serial_number or not r.serial_number_from or not r.serial_number_to or (self.serial_number >= r.serial_number_from and self.serial_number <= r.serial_number_to))
            
            if models:
                self.element_model_id = models.sorted(key=lambda r:r, reverse=True)


class maintenance_project(models.Model):
    _inherit = 'maintenance.project'
    
    @api.one
    def generate_project_budget_lines(self):
        #intervention_model_pool = self.pool.get("maintenance.intervention.model")
        
        #verifications
        if not self.date_start or not self.date_end:
            raise Warning(_('Project dates must be filled'))
        
        #find "product" and "labor time" project line type
        product_line_types = self.env['maintenance.project.budget.line.type'].search([('default_for_product','=',True)])
        if not product_line_types:
            raise Warning(_('Please set at least one project line type as default for products'))
        else:
            product_line_type_id = product_line_types[0]
        
        product_line_types = self.env['maintenance.project.budget.line.type'].search([('default_for_labor_time','=',True)])
        if not product_line_types:
            raise Warning(_('Please set at least one project line type as default for labor time'))
        else:
            labor_line_type_id = product_line_types[0]
            
        product_line_types = self.env['maintenance.project.budget.line.type'].search([('default_for_travel_cost','=',True)])
        if not product_line_types:
            raise Warning(_('Please set at least one project line type as default for travel cost'))
        else:
            travel_cost_line_type_id = product_line_types[0]
            
        if self.installation_id and self.installation_id.travel_cost_id and self.installation_id.travel_cost_id.product_id:
            travel_cost_name = self.installation_id.travel_cost_id.product_id.name
            travel_cost_product = self.installation_id.travel_cost_id.product_id
        else:
            travel_cost_name = None
            travel_cost_product = None
        
            
        #delete budget lines linked to intervention
        if self.env.context.get('regenerate',False):
            self.budget_lines.unlink()
        
            
            
        #browse generated interventions, and create budget lines in accordance with interventions
        for intervention in self.intervention_ids.filtered(lambda r:r.state!='cancel'):
            
            
            #labor cost line
            self.env['maintenance.project.budget.line'].create({
                'name':intervention.maint_type.workforce_product_id.name_get()[0][1],
                #'time_of_use':intervention.expected_time_of_use, 
                'project_id':self.id, 
                'product_id':intervention.maint_type.workforce_product_id.id,
                'sale_price':intervention.maint_type.workforce_product_id.list_price,
                'cost_price':intervention.maint_type.workforce_product_id.standard_price,  
                'quantity':intervention.time_planned/intervention.maint_type.workforce_product_duration,
                'intervention_model_id':intervention.intervention_model_id.id,  
                'budget_line_type_id':labor_line_type_id.id, 
                'intervention_id':intervention.id,
                'intervention_type_id':intervention.maint_type.id
            })
            
            #Travel cost line
            if travel_cost_name and travel_cost_product:
                self.env['maintenance.project.budget.line'].create({
                    'name':travel_cost_name,
                    #'time_of_use':intervention.expected_time_of_use, 
                    'project_id':self.id, 
                    'product_id':travel_cost_product.id,
                    'sale_price':travel_cost_product.list_price,
                    'cost_price':travel_cost_product.standard_price,  
                    'quantity':1, 
                    'intervention_model_id':intervention.intervention_model_id.id,  
                    'budget_line_type_id':travel_cost_line_type_id.id, 
                    'intervention_id':intervention.id,
                    'intervention_type_id':intervention.maint_type.id
                })
            
            #product lines
            for intervention_product in intervention.intervention_products:
                self.env['maintenance.project.budget.line'].create({
                    #'time_of_use':intervention.expected_time_of_use, 
                    'project_id':self.id,
                    'name':intervention_product.description, 
                    'product_id':intervention_product.product_id.id,
                    'sale_price':intervention_product.sale_price,
                    'cost_price':intervention_product.cost_price,  
                    'quantity':intervention_product.quantity, 
                    'intervention_product_model_id':intervention_product.intervention_product_model.id,
                    'intervention_model_id':intervention.intervention_model_id.id,  
                    'element_id':intervention_product.maintenance_element_id.id, 
                    'budget_line_type_id':product_line_type_id.id, 
                    'maintenance_product_id':intervention_product.id, 
                    'intervention_id':intervention.id, 
                    'intervention_type_id':intervention.maint_type.id
                })
        return True
    
    @api.one
    def generate_interventions(self):
        
        #delete interventions previously generated in draft state
        intervention_todelete_ids = self.env['maintenance.intervention'].search([('project_id','=',self.id),('sale_order_id','=',False)])
        intervention_todelete_ids.unlink()
  
        #generate interventions
        
        new_interventions = self.maintenance_elements.get_interventions(self)
        for new_intervention_tosave in new_interventions:
            intervention_id = self.env['maintenance.intervention'].create(new_intervention_tosave)
            
            for intervention_detail in new_intervention_tosave['intervention_detail']:
                self.env['maintenance.generation.detail'].create({
                    'intervention_id':intervention_id.id, 
                    'maintenance_element_id':intervention_detail['maintenance_element_id'], 
                    'intervention_model_id':intervention_detail['intervention_model_id']
                })                
        return True
    
    @api.one
    def get_intervention_start_date(self):
        if self.intervention_generation_start_date:
            self.used_intervention_generation_start_date = self.intervention_generation_start_date
        else:
            self.used_intervention_generation_start_date = datetime.strftime(datetime.now(), "%Y-%m-%d")
     
    intervention_ids=fields.One2many('maintenance.intervention', 'project_id', 'Expected interventions under project',help="These are interventions generated under the project. Not to be confounded with interventions history that are all the interventions done on the installation during the contract period")
    intervention_generation_type=fields.Selection([('models','From models')], string="Intervention generation",help="How to generate intervention?",default='models')
    intervention_generation_start_date=fields.Date(string="From", help="Date from which interventions will be generated",default=lambda *a:datetime.now().strftime('%Y-%m-%d'))
    used_intervention_generation_start_date=fields.Date(compute=get_intervention_start_date,string="Intervention beginning",readonly=True)


class maintenance_generation_detail(models.Model):
    _name = 'maintenance.generation.detail'
    
    intervention_model_id=fields.Many2one('maintenance.intervention.model', string="Intervention model")
    intervention_id=fields.Many2one('maintenance.intervention', string="Intervention")
    maintenance_element_id=fields.Many2one('maintenance.element', string="Maintenance element")

class maintenance_intervention_product(models.Model):
    _inherit = 'maintenance.intervention.product'
    
    @api.one
    @api.depends('intervention_id.intervention_timeofuse.expected_time_of_use')
    def _get_expected_tou(self):
        time_of_use = self.env['maintenance.intervention.timeofuse'].search([('intervention_id','=',self.intervention_id.id),('maintenance_element_id','=',self.maintenance_element_id.id)])
        if time_of_use:
            return time_of_use[0].expected_time_of_use

    intervention_product_model=fields.Many2one('maintenance.intervention.product.model', 'Product model')
    intervention_model=fields.Many2one('maintenance.intervention.model','Intervention Model')
    expected_time_of_use=fields.Float("Expected time of use",compute=_get_expected_tou,store=True) 

class maintenance_intervention(models.Model):
    _inherit = 'maintenance.intervention'
    
    @api.model
    def compute_project(self,date_start, installation_id, intervention_id=False, state=False):
        if intervention_id and self.browse(intervention_id).project_id:
            return self.browse(intervention_id).project_id
        return super(maintenance_intervention, self).compute_project(date_start, installation_id, intervention_id, state)
    
    project_id=fields.Many2one("maintenance.project", 'Project')
    project_state=fields.Selection([('draft','Draft'),('active','Active'),('disabled','Disabled')],related='project_id.state', store=True, string="Project state")
    model_and_iteration_json=fields.Text("Model and iteration") 
    intervention_model_id=fields.Many2one('maintenance.intervention.model', 'Intervention model')
    element_model_id=fields.Many2one('maintenance.element.model', 'Intervention model')    

class maintenance_installation(models.Model):
    _inherit = 'maintenance.installation'
    
    additional_labor_time=fields.Float("Additional labor time",default=1.)
    
    @api.multi
    def action_generate_project_from_installation(self):
        
        #partial_id = self.env['generate.project.wizard'].with_context(installation_ids=self._ids).create({'installation_id':self._ids[0]})
        
        context = self.env.context.copy()
        context.update({'installation_ids':self._ids})
        
        return {
            'name':_("Generate project"),
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'generate.project.wizard',
            #'res_id': partial_id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': context
        }


class maintenance_intervention_timeofuse(models.Model):
    _inherit = 'maintenance.intervention.timeofuse'
    
    @api.multi
    def check_regenerate_interventions(self):
        return True
    
        projects_to_regenerate = self.env['maintenance.project']
        for timeofuse in self:
            if timeofuse.valid and timeofuse.maintenance_element_id and timeofuse.maintenance_element_id.maintenance_projects:
                projects_to_regenerate += timeofuse.maintenance_element_id.maintenance_projects
                    
                
        projects_to_regenerate.generate_interventions_from_model()
        return True
    
    @api.multi
    def check_timeofuse(self):
        if not self.env['ir.config_parameter'].get_param('maintenance_model.timeofuse_threshold_mail',False):
            return
        
        for timeofuse in self:
            #We want to send mail only if Time of Use is going over expected time of use for active projects
            if timeofuse.valid and timeofuse.maintenance_element_id and timeofuse.maintenance_element_id.maintenance_projects.filtered(lambda r:r.state=='active'):
                #if time of use exceed expected time of use : alert 
                if timeofuse.maintenance_element_id and timeofuse.maintenance_element_id.expected_time_of_use and (timeofuse.time_of_use > timeofuse.maintenance_element_id.expected_time_of_use):
                    self._send_mail_exceeded_tou()
    
    def _send_mail_exceeded_tou(self):
        element = self.maintenance_element_id
        me = self.env.user
        if not me.default_section_id:
            return
            
        users_to_send_request=self.env['res.users'].search([('default_section_id','=',me.default_section_id.id)])
        
        subject = 'Time of use exceeded for '+element.code+' of installation '+element.installation_id.name_get()[0][1]
        body = "Time of use read : "+str(self.time_of_use)+' \nTime of use expected : '+str(self.maintenance_element_id.expected_time_of_use)
            
        for user in users_to_send_request:
            mail = {
                'email_from':self.env.user.partner_id.email, 
                'email_to':user.partner_id.email, 
                'subject':subject, 
                'body_html':body,
                'res_id':self.id,
                'model':'maintenance.intervention.timeofuse'
                #'account_id':1,
                }
            self.env['mail.mail'].create(mail)
            
        
    @api.one
    def write(self,vals):
        res = super(maintenance_intervention_timeofuse, self).write(vals)
        self.check_regenerate_interventions()
        self.check_timeofuse()
        return res
    
    @api.model
    def create(self,vals):
        res = super(maintenance_intervention_timeofuse, self).create(vals)
        res.check_regenerate_interventions()
        res.check_timeofuse()
        return res
    
    expected_time_of_use=fields.Float("Expected time of use")


class maintenance_project_budget_line(models.Model):
    _inherit = 'maintenance.project.budget.line'
    
    intervention_model_id = fields.Many2one('maintenance.intervention.model', string="Intervention Model")
    intervention_product_model_id=fields.Many2one('maintenance.intervention.product.model', string="Intervention product model")
    

class maintenance_project_budget_line_type(models.Model):
    _inherit='maintenance.project.budget.line.type'
    
    default_for_product=fields.Boolean(string='Default for Products',help='Used as default type for products generated by intervention models')
    default_for_labor_time=fields.Boolean(string='Default for Labor Time',help='Used as default type for labor time generated by intervention models')
    default_for_travel_cost=fields.Boolean(string='Default for Travel Cost',help='Used as default type for travel cost generated by intervention models')
    display_on_contract=fields.Boolean(string='Display on contract', help="Lines of this type are displayed on printed contracts")