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

from openerp import models, api

def add_one_year(d):
    if d:
        return str(int(d.split('-')[0])+1)+'-'+d.split('-')[1]+'-'+d.split('-')[2]
    return ''
def add_one_month(d):
    d.split('-')[0]
    init_year = d.split('-')[0]
    init_month = d.split('-')[1]
    init_day = d.split('-')[2]
    if init_month == '12':
        return str(int(init_year)+1)+'-01-'+init_day
    return init_year+'-'+str(int(init_month)+1)+'-'+init_day

class scheduler_maintenance_project(models.Model):
    _name = 'scheduler.maintenance_project'
    
    @api.model
    def generate_maintenance_project_invoice(self):
        
        projects_to_invoice = self.env['maintenance.project'].search([('next_invoice_date','<=',datetime.strftime(datetime.today(), '%Y-%m-%d')), ('state','=','active')])

        projects_to_invoice.generate_next_invoice()
        
        for project in projects_to_invoice:
            if project.invoicing_delay == 'monthly':
                new_next_invoice_date = add_one_month(project.next_invoice_date)
            else:
                new_next_invoice_date = add_one_year(project.next_invoice_date)
            
            project.next_invoice_date=new_next_invoice_date    
            
            #if new invoice date > end date of project, increase it
            if project.date_end and (project.date_end < new_next_invoice_date):
                if project.invoicing_delay == 'monthly':
                    project.date_end =  add_one_month(project.date_end)
                else:
                    self.date_end =  add_one_year(project.date_end)
           
        return True