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

class generate_project_wizard(models.TransientModel):
    _name = 'generate.project.wizard'
    
    @api.multi
    def generate(self):
        installation_ids = self.env.context.get("installation_ids")
        projects = self.env['maintenance.project']
        
        #create projects
        for wizard in self:
            for installation_id in installation_ids:
                if wizard.date_start > wizard.date_end:
                    raise Warning(_('Start date must be before end date'))
                projects += self.env['maintenance.project'].create({
                    'date_start':wizard.date_start, 
                    'date_end':wizard.date_end, 
                    'project_type_id':wizard.project_type_id.id, 
                    'intervention_delay_id':wizard.intervention_delay_id.id, 
                    'installation_id':installation_id, 
                    'enable':False, 
                    'maintenance_elements':[(4,elt.id) for elt in wizard.maintenance_element_ids]
                })
        #generate interventions
        projects.generate_interventions()
        return {}
    
    installation_id=fields.Many2one('maintenance.installation', 'Installations')
    date_start=fields.Date("Begin", required=True) 
    date_end=fields.Date("End", required=True)
    project_type_id=fields.Many2one('maintenance.project.type', string="Type", index=True, required=True)
    intervention_delay_id=fields.Many2one('maintenance.project.delay', string="Intervention delay", index=True, required=True)
    maintenance_element_ids=fields.Many2many('maintenance.element', 'maintenance_model_project_wizard_rel', 'wizard_id', 'element_id', 'Maintenance elements')
    