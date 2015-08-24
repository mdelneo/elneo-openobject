import logging
from openerp import models,fields,api
from openerp.exceptions import ValidationError
import re
import sys
from datetime import datetime, timedelta

class res_users(models.Model):
    _inherit = 'res.users'
    
    is_seller = fields.Boolean('Is seller') 
    days_before_quotation_relaunch = fields.Integer('Days before quotation relaunch', default=15)
    

class crm_case_stage(models.Model):
    _inherit = 'crm.case.stage'
    win_stage = fields.Boolean('Win stage')
    to_recall = fields.Boolean('To recall')
    
class crm_lead(models.Model):
    
    _inherit = ['crm.lead']
    
    _order = 'date_action desc' 
    
    @api.multi
    def print_quotation_report(self):
        return { 
                    'type': 'ir.actions.report.xml',
                    'report_name':'sale.quotation.lead',
                    'nodestroy': True,
                    'datas':{'model':'crm.lead', 'ids': [l.id for l in self]},
                } 
    
    @api.multi
    def _get_quotation_fields(self):
        for opportunity in self:
            #find last quotation
            if opportunity.quotation_ids:
                last_quotation = opportunity.quotation_ids[0]
            else:
                last_quotation = None
                
            if last_quotation:
                opportunity.last_quotation_id = last_quotation.id
                opportunity.quotation_address_id = last_quotation.quotation_address_id.id
            else:
                opportunity.last_quotation_id = None
                opportunity.quotation_address_id = opportunity.partner_address_id.id
            
            if opportunity.planned_revenue_auto:
                if last_quotation:
                    opportunity.planned_revenue_computed = last_quotation.margin
                else:
                    opportunity.planned_revenue_computed = 0
            else:
                opportunity.planned_revenue_computed = opportunity.planned_revenue
            
                    
            if opportunity.sale_price_auto:
                if last_quotation:
                    opportunity.sale_price_computed = last_quotation.amount_untaxed
                else:
                    opportunity.sale_price_computed = 0
            else:
                opportunity.sale_price_computed = opportunity.sale_price_manual
        
    
    @api.multi
    def _get_torecall(self):
        stage_torecall_ids = self.env["crm.case.stage"].search([('type','=','opportunity'),('to_recall','=',True)])
        for opportunity in self:
            if opportunity.date_action <= datetime.strftime(datetime.today(), '%Y-%m-%d') and opportunity.stage_id.id in stage_torecall_ids:
                opportunity.to_recall = True
            else:
                opportunity.to_recall = False
    
    
    def _search_torecall(self, operator, value):
        stage_torecall_ids = self.env["crm.case.stage"].search([('type','=','opportunity'),('to_recall','=',True)])
        return ['&',('stage_id','in',[s.id for s in stage_torecall_ids]),('date_action','<=',datetime.strftime(datetime.today(), '%Y-%m-%d'))]


    @api.model
    def _get_default_stage_id(self):
        stage = self.env["crm.case.stage"].search([('type','=','opportunity')], order='sequence', limit=1)
        if stage:
            return stage.id
        return None
    
    
    
    quotation_ids = fields.One2many('sale.order', 'opportunity_id', 'Quotations')
    planned_revenue_auto = fields.Boolean('Auto margin', default=True)
    planned_revenue_computed = fields.Float(compute='_get_quotation_fields', string='Margin', method=True, readonly=True)
    sale_price_computed = fields.Float(compute='_get_quotation_fields', string='Sale price', method=True, readonly=True) 
    sale_price_manual = fields.Float('Sale price (manual)')
    sale_price_auto = fields.Boolean('Sale price auto ?', default=True)
    to_recall = fields.Boolean(compute='_get_torecall', search=_search_torecall, string='To recall', type="boolean", method=True)
    last_quotation_id = fields.Many2one('sale.order', compute='_get_quotation_fields', string="Last quotation", method=True, readonly=True, help='Last quotation related to this opportunity.')
    quotation_address_id = fields.Many2one('res.partner.address', compute='_get_quotation_fields', string="Quotation address", method=True, readonly=True, help='Last quotation related to this opportunity.')
    
    @api.model
    def default_get(self, fields_list):
        res = super(crm_lead, self).default_get(fields_list)
        res['stage_id'] = self._get_default_stage_id()
        res['state'] = 'open'
        res['date_action'] = (datetime.now()+timedelta(days=self.env['res.users'].browse(self._uid).days_before_quotation_relaunch)).strftime('%Y-%m-%d')
        res['user_id'] = self._uid
        return res
    
    
    #display notification number of opportunity to recall 
    @api.model
    def _needaction_domain_get(self):
        return ['&',('user_id','=',self._uid),('to_recall','=',True)]
    
    
    @api.model
    def _needaction_count(self, domain):
        res = super(crm_lead, self)._needaction_count(domain)
        return res
    
crm_lead()

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    @api.onchange('last_quotation_id')
    def on_change_last_quotation(self):
        if self.last_quotation_id:
            self.opportunity_id = self.last_quotation_id.opportunity_id.id
    
    @api.multi
    def action_button_confirm(self):
        res = super(sale_order,self).action_button_confirm()
        self.action_win()
        return res
    
    @api.multi
    def action_win(self):
        win_stage = self.env["crm.case.stage"].search([('type','=','opportunity'),('win_stage','=',True)])
        if not win_stage:
            return False
        for sale in self:
            if sale.opportunity_id and not sale.opportunity_id.stage_id.win_stage:
                sale.opportunity_id.stage_id = win_stage[0].id
        return True

    #delete opportunity when we delete sale
    @api.multi
    def unlink(self):
        for sale in self:
            if sale.opportunity_id:
                sale.opportunity_id.unlink()
        res = super(sale_order,self).unlink()
        return res
    
    @api.model
    def create(self, vals):
        res = super(sale_order,self).create(vals)
        res.create_opportunity()
        return res
    
    @api.multi
    def write(self, vals):
        res = super(sale_order,self).write(vals)
        self.create_opportunity()
        return res
    
    @api.multi
    def create_opportunity(self):
        if self._context and self._context.get('copy',False):
            return True
        
        #if quotation is not linked to opportunity : create it
        for sale in self:
            if sale.origin_type == 'quotation' and not sale.opportunity_id:
                if sale.last_quotation_id and sale.last_quotation_id.opportunity_id:
                    opportunity_id = sale.last_quotation_id.opportunity_id.id
                else:
                    opportunity_id = self.env["crm.lead"].create({
                        'name':sale.name,
                        'partner_id':sale.partner_id.id,
                        'partner_address_id':sale.quotation_address_id and sale.quotation_address_id.id or sale.partner_order_id.id,
                        'user_id':sale.user_id.id, 
                        'type':'opportunity'
                    })
                sale.opportunity_id = opportunity_id
        return True        
    
    @api.multi
    def copy(self, default=None):
        default['opportunity_id'] = None
        default['last_quotation_id'] = None
        return super(sale_order, self.with_context(copy=True)).copy(default)
                
    opportunity_id = fields.Many2one('crm.lead', 'Opportunity', readonly=True)
    origin_type = fields.Selection([('quotation','Quotation'),('order','Order')],'Type', help='Type is quotation if order come from a quotation') 
    last_quotation_id = fields.Many2one('sale.order', string="Last quotation", help='When you select last quotation done to this customer, good opportunity will be automatically selected.') 
    
    @api.model
    def default_get(self, fields_list):
        res = super(sale_order, self).default_get(fields_list)
        res['origin_type'] = self.env['res.users'].browse(self._uid).is_seller and 'quotation' or 'order'
        return res
    
sale_order()