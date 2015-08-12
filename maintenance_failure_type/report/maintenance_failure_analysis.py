# -*- encoding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from openerp import tools
from openerp.osv import fields, osv

from openerp import models, fields

class maintenace_failure_report(osv.osv):
    _name = "maintenance.failure.report"
    _description = "Maintenance Failure Analysis"
    _auto = False
    
    name = fields.Char('Year', required=False,readonly=True)
    brand = fields.Many2one('maintenance.element.brand','Brand', readonly=True)
    intervention_id=fields.Many2one('maintenance.intervention','Intervention', readonly=True)
    nbr = fields.Integer('# of Interventions', readonly=True)
    date_start = fields.Datetime('Start Date', readonly=True)
    date_end = fields.Datetime('End Date', readonly=True)
    effective_duration = fields.Datetime('Effective Duration')
    failure_type_id = fields.Many2one('maintenance.failure.type','Failure Type', readonly=True)
    failure_element_id = fields.Many2one('maintenance.element', 'Element damaged',readonly=True)
    partner_id = fields.Many2one('res.partner','Partner',readonly=True)
    time_planned = fields.Float('Time Planned',readonly=True)
    
    
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'maintenance_failure_report')
        cr.execute("""
            CREATE view maintenance_failure_report as
              SELECT
                    (select 1 ) AS nbr,
                    i.id as id,
                    i.id as intervention_id,
                    i.date_start as date_start,
                    i.date_end as date_end,
                    (DATE_PART('day', MAX(mit.date_end)::timestamp - i.date_start::timestamp) * 24 + 
               DATE_PART('hour', MAX(mit.date_end)::timestamp - i.date_start::timestamp)) as effective_duration,
                    i.time_planned,
                    i.installation_id,
                    i.failure_type_id,
                    i.failure_element_id,
                    me.brand,
                    mi.partner_id
              FROM maintenance_intervention i
              JOIN maintenance_installation mi ON i.installation_id = mi.id
              JOIN maintenance_intervention_task mit ON i.id = mit.intervention_id 
              JOIN maintenance_element me ON me.id = i.failure_element_id
                GROUP BY
                    i.id,
                    i.date_start,
                    i.date_end,
                    time_planned,
                    i.installation_id,
                    failure_type_id,
                    failure_element_id,
                    me.brand,
                    mi.partner_id
        """)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
