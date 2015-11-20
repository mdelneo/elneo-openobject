'''
SELECT maintenance_element_id, time_of_use, date, 
    (SELECT time_of_use FROM maintenance_intervention_timeofuse mit1
    WHERE mit1.date < mit.date
    AND mit1.maintenance_element_id = mit.maintenance_element_id
    AND mit1.time_of_use IS NOT NULL
    ORDER BY date DESC
    LIMIT 1),
    (SELECT date FROM maintenance_intervention_timeofuse mit1
    WHERE mit1.date < mit.date
    AND mit1.maintenance_element_id = mit.maintenance_element_id
    AND mit1.time_of_use IS NOT NULL
    ORDER BY date DESC
    LIMIT 1)

FROM maintenance_intervention_timeofuse mit
WHERE time_of_use IS NOT NULL
GROUP BY maintenance_element_id, date, time_of_use
ORDER BY maintenance_element_id,date

'''
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

class maintenance_timeofuse_report(osv.osv):
    _name = "maintenance.timeofuse.report"
    _description = "Maintenance Time of Use Analysis"
    _auto = False
    
    #name = fields.Char('Year', required=False,readonly=True)
    #brand = fields.Many2one('maintenance.element.brand','Brand', readonly=True)
    installation_id=fields.Many2one('maintenance.installation','Installation', readonly=True)
    nbr = fields.Integer('# of Counters', readonly=True)
    #date_start = fields.Datetime('Start Date', readonly=True)
    #date_end = fields.Datetime('End Date', readonly=True)
    use = fields.Integer('Use')
    #failure_type_id = fields.Many2one('maintenance.failure.type','Failure Type', readonly=True)
    element_id = fields.Many2one('maintenance.element', 'Element concerned',readonly=True)
    partner_id = fields.Many2one('res.partner','Partner',readonly=True)
    date = fields.Datetime('Date',readonly=True)
    time_of_use = fields.Integer('Time of Use',readonly=True)
    previous_date = fields.Datetime('Previous Date',readonly=True)
    previous_time_of_use = fields.Integer('Previous Time of Use',readonly=True)
    
    
    #time_planned = fields.Float('Time Planned',readonly=True)
    
    
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'maintenance_timeofuse_report')
        cr.execute("""
            DROP VIEW IF EXISTS maintenance_timeofuse_report;
            CREATE view maintenance_timeofuse_report as
                            SELECT min(req1.maintenance_element_id) AS id,
                        ( SELECT 1) AS nbr,
                        rp.id AS partner_id,
                        mi.id AS installation_id,
                        req1.maintenance_element_id AS element_id,
                        req1.time_of_use,
                        req1.date,
                        req1.previous_time_of_use,
                        req1.previous_date,
                        (req1.time_of_use - req1.previous_time_of_use)::integer AS use
                       FROM ( SELECT mit.maintenance_element_id,
                                mit.time_of_use,
                                mit.date,
                                ( SELECT mit1.time_of_use
                                       FROM maintenance_intervention_timeofuse mit1
                                      WHERE mit1.date < mit.date AND mit1.maintenance_element_id = mit.maintenance_element_id AND mit1.time_of_use IS NOT NULL
                                      ORDER BY mit1.date DESC
                                     LIMIT 1) AS previous_time_of_use,
                                ( SELECT mit1.date
                                       FROM maintenance_intervention_timeofuse mit1
                                      WHERE mit1.date < mit.date AND mit1.maintenance_element_id = mit.maintenance_element_id AND mit1.time_of_use IS NOT NULL
                                      ORDER BY mit1.date DESC
                                     LIMIT 1) AS previous_date
                               FROM maintenance_intervention_timeofuse mit
                              WHERE mit.time_of_use IS NOT NULL
                              GROUP BY mit.maintenance_element_id, mit.date, mit.time_of_use
                              ORDER BY mit.maintenance_element_id, mit.date) req1
                         JOIN maintenance_element me ON me.id = req1.maintenance_element_id
                         JOIN maintenance_installation mi ON me.installation_id = mi.id
                         JOIN res_partner rp ON rp.id = mi.partner_id
                      GROUP BY element_id, mi.id, rp.id, me.id, req1.time_of_use, req1.date, req1.previous_time_of_use, req1.previous_date
                    ORDER BY element_id
                      ;

        """)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
