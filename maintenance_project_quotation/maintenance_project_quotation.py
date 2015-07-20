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

from datetime import datetime
from openerp import models, fields, api, _



class maintenance_project_quotation_price(models.Model):
    _name = 'maintenance.project.quotation.price'
    
    @api.onchange('brut_sale_price','cost_price','discount')
    def compute_prices(self):
        self._compute_prices()

    @api.one
    def _compute_prices(self):
        
        self.net_sale_price = self.brut_sale_price*(1-(self.discount/100.))
        
        if self.cost_price:
            self.coefficient = self.net_sale_price/self.cost_price
        else:
            self.coefficient = 0
        self.margin = self.net_sale_price - self.cost_price
        
        years = None
        #number of year of project
        if self.project_id.date_end and self.project_id.date_start:
            years = (datetime.strptime(self.project_id.date_end,'%Y-%m-%d')-datetime.strptime(self.project_id.date_start,'%Y-%m-%d')).days/365.
        if years:
            self.annual_net_sale_price = self.net_sale_price/years
        else:
            self.annual_net_sale_price = 0
    
    
    project_id=fields.Many2one('maintenance.project', 'Project',help="The project linked to this price")
    project_type_id=fields.Many2one('maintenance.project.type', string="Project")
    brut_sale_price=fields.Float('Brut sale price', help="Sale price for the duration of the project")
    cost_price=fields.Float('Cost price', help="Cost price for the duration of the project") 
    discount=fields.Float('Discount', help="Discount in %")        
    coefficient=fields.Float(compute=_compute_prices, string="Coefficient", readonly=True,help="The coefficient = Net Sale Price / Cost Price")
    margin=fields.Float(compute=_compute_prices, string="Margin", readonly=True,help="The margin = Net Sale Price - Cost Price")
    net_sale_price=fields.Float(compute=_compute_prices, string="Net sale price", help="Net sale price for the duration of the project (Brut Sale Price * Discount)", readonly=True)
    annual_net_sale_price=fields.Float(compute=_compute_prices, string="Annual sale price", help="Annual net sale price (Net Sale Price / Years of duration)",readonly=True)

class maintenance_installation(models.Model):
    _inherit = 'maintenance.installation'
    
    @api.one
    def installation_quotation(self):
        self.state='quotation'
    
    def installation_draft(self):
        self.state = 'draft'
    
    state=fields.Selection([('draft','Draft'),('quotation','Quotation'),('active', 'Active'), ('inactive','Inactive')], string="State", readonly=True)
    is_quotation_installation=fields.Boolean('Quotation installation', help="Installation created by a request for quotation of maintenance project.")
    

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    installation_id=fields.Many2one('maintenance.installation', 'Installation')
    maintenance_project_id=fields.Many2one('maintenance.project', 'Maintenance project')
    
    
    def copy(self,default=None):
        if not default:
            default = {}
        default['installation_id'] = None
        default['maintenance_project_id'] = None
        return super(sale_order, self).copy(default)

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    product_type=fields.Text('product_id.type',store=True)
    

# Extend the maintenance_project class to add quotation process 
class maintenance_project(models.Model):
    _inherit='maintenance.project'
    
    state=fields.Selection(selection=[('draft','Draft'),('quotation_todo','Quote To Do'),('quotation_done','Quote Done'),('active','Active'),('disabled','Disabled')])
    quotation_todo_date=fields.Datetime('Ask Date',readonly=True, translate=True)
    quotation_done_date=fields.Datetime('Date Done',readonly=True,translate=True)
    quotation_prices=fields.One2many('maintenance.project.quotation.price', 'project_id', 'Quotation prices')
    
    @api.one
    def _get_mail_users(self):
    #TODO: Add filter in another module to filter Project Warehouse with user warehouse - In order to extend it easily, created function _get_mail_users
        """
        @return users:A recordset with users
        """
        users = self.env['res.users'].search([('receive_project_quotation_request','=',True)])

        return users
 
    # Send a mail to people that belongs to the same sale shop and
    # whom have checked that they want to be warned
    @api.one
    def _send_todo_mail(self):
        res = False
            
        if (not self.sale_order_id):
            return False

        
        body=_('A new maintenance quotation(Project : %s) has just been asked by %s<br/>')%(self.code,self.env.user.name)


        
        
        for user in self._get_mail_users():
            self.env['mail.mail'].create({
                                           'email_from':self.env.user.partner_id.email, 
                                            'email_to':user.partner_id.email, 
                                            'subject':_('New maintenance quotation asked: %s')%(self.code),
                                            'body_html':body,
                                            'res_id':self.id,
                                            'model':'maintenance.project'
                                           })
            res=True

        return res
    
    # Send a confirmation mail to the salesman linked to the sale
    @api.one
    def _send_done_mail(self):
        res = False
            
        if (not self.sale_order_id):
            return False

        
        body=_('A maintenance quotation(%s) has just been done by %s<br/>')%(self.code,self.env.user.name)


        
        
        for user in self._get_mail_users():
            self.env['mail.mail'].create({
                                           'email_from':self.env.user, 
                                            'email_to':user.partner_id.email, 
                                            'subject':_('Maintenance quotation done: %s')%(maintenance_project.code),
                                            'body_html':body,
                                            'res_id':self.id,
                                            'model':'maintenance.project'
                                           })
            res=True

        return res
        
    @api.one
    def draft(self):
        self.state='draft'
        
    @api.one
    def quotation_todo(self):
        self.state='quotation_todo'
        self.quotation_todo_date=datetime.now()
        self._send_todo_mail()
        return True

    @api.one
    def quotation_done(self):
        self.state='quotation_done'
        self.quotation_done_date=datetime.now()
        self._send_done_mail()
        
    @api.one
    def active(self):
        self.state='active'
        
    @api.one
    def disabled(self):
        self.state='disabled'
        
    ''' UNUSED
    def _get_status(self,cr,uid,ids):
        
        
        return False
    '''
    
    @api.one
    def generate_quotation_prices(self):

            
        for project_type in self.env['maintenance.project.type'].search([]):
            
            #find contract type and associated budget rules
            budget_rules = self.env['maintenance.project.budget.rule'].search([('project_type_id','=',project_type.id)])
            
            total_cost_price = 0
            total_sale_price = 0 
            for budget_line in self.budget_lines:
                budget = budget_rules.filtered(lambda r:r.intervention_type_id == budget_line.intervention_type_id)
                if not budget_line.intervention_type_id or not budget.mapped('budget_line_type_id'):
                    raise Warning(_('Please configure budget rule for project type "%s", intervention type "%s" and budget line type "%s".')%(project_type.name,budget_line.intervention_type_id.name,budget_line.budget_line_type_id.name))
            
            
                if budget.mapped('budget_line_type_id'):
                    total_cost_price = total_cost_price + budget_line.cost_price*budget_line.quantity
                    total_sale_price = total_sale_price + budget_line.sale_price*budget_line.quantity
            
            self.env['maintenance.project.quotation.price'].create({
                'project_id':self.id, 
                'project_type_id':project_type.id, 
                'brut_sale_price':total_sale_price, 
                'cost_price':total_cost_price
                })
            
            
                
        return True
