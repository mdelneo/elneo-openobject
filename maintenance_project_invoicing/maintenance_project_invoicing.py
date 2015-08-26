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

from dateutil.relativedelta import relativedelta

from openerp import models, fields, api, _

def add_one_year(d):
    return datetime.strftime(datetime.strptime(d,'%Y-%m-%d')+relativedelta(years=1),'%Y-%m-%d')

def add_one_month(d):
    return datetime.strftime(datetime.strptime(d,'%Y-%m-%d')+relativedelta(months=1),'%Y-%m-%d')

def decrease_one_year(d):
    return datetime.strftime(datetime.strptime(d,'%Y-%m-%d')+relativedelta(years=-1),'%Y-%m-%d')

def decrease_one_month(d):
    return datetime.strftime(datetime.strptime(d,'%Y-%m-%d')+relativedelta(months=-1),'%Y-%m-%d')


'''
class maintenance_intervention(models.Model):
    _inherit = 'maintenance.intervention'
    
    @api.one
    def generate_invoice(self):
        invoice = super(maintenance_intervention, self).generate_invoice()
        
        maintenance_project_pool = self.pool.get("maintenance.project")
        #recompute costs of project
        
        project = intervention.maintenance_project_id
        if project:
            maintenance_project_pool.compute_cost_price(cr, uid, [project.id], date=intervention.date_start, context=context)

        return invoice_ids
    
maintenance_intervention()
'''


class maintenance_project(models.Model):
    _inherit = 'maintenance.project' 
    
    #return date when first interventions must be associated to invoice 
    @api.model
    def find_invoice_start_date(self, date_invoice, project, force_annual = False):
        '''
        Example : 
        
        for a project from 15/02/2013
        we like to find interventions for invoice of 15/12/2013 :
            - does 15/02/2013 > 15/12/2013 : NO
            - does 15/02/2014 > 15/12/2013 : YES
        Invoice concern intervention from 15/02/2014 to 14/02/2015
        '''
        if project.project_start_period_invoicing:
            project_date = project.project_start_period_invoicing
        else:
            project_date = project.date_start
            
        if project_date:
            while date_invoice > project_date:
                if not force_annual and project.invoicing_delay == 'monthly':
                    project_date = add_one_month(project_date)
                else:
                    project_date = add_one_year(project_date)
                    
        return project_date
        
    
    #recompute cost price of invoice of specified date
    #if no date specified : recompute all cost prices of all invoices linked to project
    def compute_cost_price(self, cr, uid, ids, date=None, context=None):
        intervention_pool = self.pool.get("maintenance.intervention")
        project_pool = self.pool.get("maintenance.project")
        
        for project in self.browse(cr, uid, ids, context):
            project_invoice_lines =[]
            
            if date:
                current_invoice_line = self.get_project_invoice_lines_from_date(cr, uid, [project.id], date, context)[project.id]
                if not current_invoice_line:
                    continue
                
                project_invoice_lines = [current_invoice_line]
            else:
                project_invoice_lines = []
                for order_line in project.sale_order_id.order_line:
                    for invoice_line in order_line.invoice_lines:
                        project_invoice_lines.append(invoice_line)
                
            for project_invoice_line in project_invoice_lines:
                
                date_start = self.find_invoice_start_date(project_invoice_line.invoice_id.date_invoice, project)
                
                if project.invoicing_delay == 'monthly':
                    date_end = add_one_month(date_start)
                else:
                    date_end = add_one_year(date_start)
                    
                intervention_ids = intervention_pool.search(cr, uid, 
                    [
                        ('installation_id','=',project.installation_id.id),
                        ('date_start','>=',date_start), 
                        ('date_end','<',date_end),
                         ('state','=','done')
                    ])
                
                #list all invoices of interventions
                cost_price_project_discount = 0
                
                intervention_invoices = {}
                for intervention in intervention_pool.browse(cr, uid, intervention_ids, context=context):
                    for intervention_invoice in intervention.sale_order_id.invoice_ids:
                        if not intervention_invoices.has_key(intervention_invoice.id):
                            intervention_invoices[intervention_invoice.id] = {'invoice':intervention_invoice, 'intervention':intervention}
                            
                for intervention_invoice_id in intervention_invoices:
                    intervention_invoice = intervention_invoices[intervention_invoice_id]['invoice']
                    intervention = intervention_invoices[intervention_invoice_id]['intervention']
                    for intervention_invoice_line in intervention_invoice.invoice_line:
                        #get invoiced percent
                        invoiced_percent = intervention_invoice_line.maintenance_invoiced_percent
                        if invoiced_percent < 100:
                            ###############
                            ### WARNING ###
                            ###############
                            # cost price of current invoice must be calculated BEFORE addition of costs prices. 
                            # It's calculated in the SAME function, in elneo_maintenance module, and order of calls of SUPER method depends on module inheritance
                            # So : elneo_maintenance_project_invoicing must inherit elneo_maintenance.
                            ###############
                            cost_price_project_discount += intervention_invoice_line.cost_price*intervention_invoice_line.quantity
                
                if project_invoice_line.product_id.id == project.project_type_id.product_id.id:
                    ''#self.pool.get("account.invoice.line").write(cr, uid, [project_invoice_line.id], {'cost_price':cost_price_project_discount})
        return True
    
    #return concerned invoice of contract, for date passed by parameter
    '''
    Example : 
    one maintenance project from 14/02/2013 to 14/02/2018
    1st invoice : 01/02/2013 -> concern interventions from 14/02/2013 to 15/02/2014
    2nd invoice : 15/12/2013 -> concern interventions from 14/02/2014 to 15/02/2015
    3rd invoice : 15/12/2014 -> concern interventions from 14/02/2015 to 15/02/2016
    
    if we want to know which invoice is for intervention of 16/02/2014
    program try: 
    does 14/02/2013 <= 16/02/2014 : YES -> set 15/02/2013 as previous_date
    does 14/02/2014 <= 16/02/2014 : YES -> set 15/02/2014 as previous_date
    does 14/02/2015 <= 16/02/2014 : NO
    
    know we can find last invoice before previous_date (15/02/2014)
    we sort all invoices of project by date descending and we try : 
    does 14/02/2014 >= 15/12/2014 -> NO
    does 14/02/2014 >= 15/12/2013 -> YES -> good invoice is invoice of 15/12/2013
    '''    
    def get_project_invoice_lines_from_date(self, cr, uid, ids, date=None, context=None):
        result = {}
        
        
        if not date:
            date = datetime.strftime('%Y-%m-%d')
        for project in self.browse(cr, uid, ids, context):

            #if date not in project period            
            if project.date_start > date:
                result[project.id] = None
            
            if project.project_start_period_invoicing:
                project_date = project.project_start_period_invoicing
            else:
                project_date = project.date_start
                
            previous_date = None
            while project_date <= date:
                previous_date = project_date
                if project.invoicing_delay == 'monthly':
                    project_date = add_one_month(project_date)
                else:
                    project_date = add_one_year(project_date)
            
            #find last invoice before this date
            invoice_lines_by_date = []
            if project.sale_order_id:
                for order_line in project.sale_order_id.order_line:
                    for invoice_line in order_line.invoice_lines:
                        invoice_lines_by_date.append({'date':invoice_line.invoice_id.date_invoice, 'invoice_line':invoice_line})
            invoice_lines_by_date = sorted(invoice_lines_by_date, key=lambda invoice: invoice['date'], reverse=True)
            
            invoice_line_by_date = None
            for invoice_line_by_date in invoice_lines_by_date:
                if previous_date >= invoice_line_by_date['date']:
                    break
                
            if invoice_line_by_date and invoice_line_by_date:  
                result[project.id] = invoice_line_by_date['invoice_line']
            else:
                result[project.id] = None
        
        return result    
    
    def format_date(self, cr, uid, date, context):
        return datetime.strptime(date, '%Y-%m-%d').strftime('%d/%m/%Y')
    
    
    @api.one
    def generate_next_invoice(self):

        date_invoice = self.next_invoice_date
        
        if not date_invoice:
            date_invoice = datetime.today().strftime("%Y-%m-%d")
        if not date_invoice or not self.sale_order_id:
            return
        
        date_start = self.find_invoice_start_date(date_invoice, self)
        
        if not date_start:
            return
        
        if self.invoicing_delay == 'monthly':
            date_end = add_one_month(date_start)
        else:
            date_end = add_one_year(date_start)
            
        date_end = datetime.strftime(datetime.strptime(date_end,'%Y-%m-%d')+relativedelta(days=-1),'%Y-%m-%d')
        
        #set invoiced = False to allow action_invoice_create to recreate another invoice for the same line
        #TODO: REMOVE WHEN sale/sale.py is fixed (in action_invoice_create)
        if len(self.sale_order_id.order_line) == 1:
            self.env.cr.execute("""UPDATE sale_order_line SET invoiced=False WHERE id IN (%s)""",(tuple(self.sale_order_id.order_line._ids)))
            self.env['sale.order.line'].invalidate_cache(['invoiced'])
        elif len(self.sale_order_id.order_line) > 1:
            self.env.cr.execute("""UPDATE sale_order_line SET invoiced=False WHERE id IN (%s)""",(tuple(self.sale_order_id.order_line._ids)))
            self.env['sale.order.line'].invalidate_cache(['invoiced'])
        
        invoice_id = self.sale_order_id.action_invoice_create()
        
        if not invoice_id:
            return False
        
        invoice = self.env['account.invoice'].browse(invoice_id)
        
        lines_to_delete = self.env['account.invoice.line']
       
        comment = "" 
        invoice_name = ''
        for line in invoice.invoice_line:
            if round(line.price_unit,2) != round(self.annual_amount,2):
                lines_to_delete+=line
            elif line.product_id.id == self.project_type_id.product_id.id:
                date_start_str = self.format_date(date_start)
                date_end_str = self.format_date(date_end)
                invoice_name = ''
                if self.installation_id and self.installation_id.name:
                    invoice_name = '['+self.installation_id.name+'] '
                invoice_name = line.name+" ["+date_start_str+" - "+date_end_str+"]"
                
                price = 0
                if self.invoicing_delay == 'monthly':
                    price = self.current_price/12
                else:
                    price = self.current_price
                
                line.price_unit = price
                line.name = invoice_name
                
        #delete lines generated from old invoices
        lines_to_delete.unlink()
            
        invoice.name = invoice_name
        invoice.comment = comment
        invoice.button_reset_taxes()
                        
        return True 

    @api.one
    @api.depends('annual_amount','delay_price_init')
    def _get_current_price(self):
        
        self.current_price = 0.0
        self.price_calculation = ''
        
        if not self.annual_amount:
            self.price_calculation = _('No initial annual amount')
        elif self.delay_price_init is False:
            self.price_calculation = _('Unable to find initial price delay')
        else:
            current_price = (self.annual_amount+self.delay_price_init)
            self.current_price = current_price
            self.price_calculation = '(('+str(self.annual_amount)+'+'+str(self.delay_price_init)+') = '+str(self.current_price)
                    
    @api.one
    def write(self, vals):
        res = super(maintenance_project, self).write(vals)
        if 'annual_amount' in vals:
            if self.sale_order_id:
                lines = self.env['sale.order'].search([('order_id','=',self.sale_order_id.id),('product_id','=',self.project_type_id.product_id.id)])
                lines.price_unit=self.annual_amount
        return res
    
    @api.onchange('intervention_delay_id')
    @api.one
    def onchange_intervention_delay(self):
        if self.intervention_delay_id and not self.delay_price_included:
            self.delay_price_init = self.intervention_delay_id.price
            
            
    next_invoice_date=fields.Date('Next invoice date') 
    project_start_period_invoicing = fields.Date("Start of invoicing period")
    invoicing_delay = fields.Selection([('annual', 'Annual'),('monthly', 'Monthly')],"Invoicing delay", default='annual',required=True)
    annual_amount = fields.Float("Initial annual amount (without delay additional amount)")
    delay_price_init = fields.Float("Initial delay price")
    delay_price_included = fields.Boolean("Delay price included in initial price")
    price_calculation = fields.Char(compute=_get_current_price, string="Calculation", size=255, help="(annual amount + delay price)", store=True)
    current_price = fields.Float(compute=_get_current_price, string="Current annual amount", store=True)    
