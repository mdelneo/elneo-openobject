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

from openerp import models, fields, api, _
from openerp.exceptions import Warning


class maintenance_element_brand(models.Model):
    _name='maintenance.element.brand'
    
    name = fields.Char(size=255, string="Name")
    
class maintenance_element(models.Model):
    _inherit = 'maintenance.element'
    
    brand = fields.Many2one('maintenance.element.brand','Brand')

class maintenance_intervention_type(models.Model):
    _inherit = 'maintenance.intervention.type'
    
    is_reparation=fields.Boolean('Is reparation', help='Depending on this field, user must complete reparation type before closing intervention')
    
    
class maintenance_failure_type(models.Model):
    _name = 'maintenance.failure.type'
    
    name = fields.Char(string='Name',size=255, translate=True)
    description = fields.Text(string='Description',translate=True)  
    

class maintenance_intervention(models.Model):
    _inherit='maintenance.intervention'
    
    failure_type_id = fields.Many2one('maintenance.failure.type', 'Failure type')
    failure_element_id = fields.Many2one('maintenance.element', 'Element damaged')
    
    @api.multi
    def action_done(self):
        if self.maint_type and self.maint_type.is_reparation and (not self.failure_type_id or not self.failure_element_id):
                raise Warning( _('For a reparation you must complete type of failure and element damaged.'))
        return super(maintenance_intervention,self).action_done()
