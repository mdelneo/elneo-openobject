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


class maintenance_project(models.Model):
    _inherit = 'maintenance.project' 

    def format_date(self, cr, uid, date, context):
        return datetime.strptime(date, '%Y-%m-%d').strftime('%d/%m/%Y')
    
    @api.one
    def _set_cpi(self):
        cpi_pool = self.env['cpi.be.entry']
        
        res = self._get_invoice_dates()
        date_invoice=res['date_invoice']
        date_start = res['date_start']
        date_end = res['date_end']
        
        if not date_invoice or not self.sale_order_id or not date_start:
            return False
        
        #Find new CPI
        recompute_cpi = False
        if self.invoicing_delay == 'annual':
            recompute_cpi = True
        else:
            #in case of monthly invoicing, if one year is passed, recompute CPI
            if self.find_invoice_start_date(date_invoice, self, force_annual=True) == date_start:
                recompute_cpi = True
        
        if recompute_cpi:
            cpi_date = datetime.strptime(date_invoice, '%Y-%m-%d')
            cpi_month = cpi_date.month
            cpi_year = cpi_date.year
            current_cpi_ids = cpi_pool.search([('type_id','=',self.cpi_type_id.id), ('year','=',cpi_year), ('month','=',cpi_month)])
        
            #if no CPI found, try to found it for previous month
            if not current_cpi_ids:
                cpi_date = datetime.strptime(decrease_one_month(date_invoice), '%Y-%m-%d')
                cpi_month = cpi_date.month
                cpi_year = cpi_date.year
                current_cpi_ids = cpi_pool.search([('type_id','=',self.cpi_type_id.id), ('year','=',cpi_year), ('month','=',cpi_month)])
                
            #if CPI decrease relative to CPI of last year/month : use last CPI
            last_cpi_ids = None
            last_cpi_ids = cpi_pool.search([('type_id','=',self.cpi_type_id.id), ('year','>=',self.initial_cpi_id.year), ('year','=',cpi_year-1), ('month','=',cpi_month)])
            
            if last_cpi_ids and current_cpi_ids:
                last_cpi_value = last_cpi_ids[0].value
                current_cpi_value = current_cpi_ids[0].value
                if current_cpi_value < last_cpi_value:
                    current_cpi_ids = last_cpi_ids
                
            if current_cpi_ids:
                self.current_cpi_id = current_cpi_ids[0]
                
        else: # not recompute CPI
            current_cpi_ids = [self.current_cpi_id.id]
            
    @api.one
    @api.depends('annual_amount','delay_price_init','initial_cpi_id','current_cpi_id')
    def _get_current_price(self):
        
        self.current_price = 0.0
        self.price_calculation = ''
        
        if not self.annual_amount:
            self.price_calculation = _('No initial annual amount')
        elif self.delay_price_init is False:
            self.price_calculation = _('Unable to find initial price delay')
        elif not self.initial_cpi_id:
                self.price_calculation = _('No initial CPI value')
        elif not self.current_cpi_id:
            self.price_calculation = _('No current CPI')
        else:
            current_price = ((self.annual_amount+self.delay_price_init) / self.initial_cpi_id.value) * self.current_cpi_id.value
            self.current_price = current_price
            self.price_calculation = '(('+str(self.annual_amount)+'+'+str(self.delay_price_init)+')/'+str(self.initial_cpi_id.value)+')*'+str(self.current_cpi_id.value)+' = '+str(self.current_price)       
    
    @api.one
    def generate_next_invoice(self):

        #Set CPI before generating invoice
        self._set_cpi()

        res = super(maintenance_project,self).generate_next_invoice()
            
        return res
    
    @api.multi
    def _get_default_cpi_type(self):
        type_id = self.env['ir.config_parameter'].get_param('elneo_maintenance_project_invoicing.default_cpi_type',False)
        if type_id != 'False':
            type_id = int(type_id)
        else:
            type_id = False
        return type_id
    
    price_calculation = fields.Char(compute=_get_current_price)
    current_price = fields.Float(compute=_get_current_price)
    initial_cpi_id = fields.Many2one("cpi.be.entry", string="Initial CPI")
    cpi_type_id = fields.Many2one('cpi.be.type', "CPI type",default=_get_default_cpi_type)
    current_cpi_id = fields.Many2one("cpi.be.entry", string="Current CPI")
      