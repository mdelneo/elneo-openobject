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

from openerp import models, fields, api
import os


class ProductionServer(models.TransientModel):
    _name='production.server'
    
    
    @api.model
    def is_production_server(self):
        production_server = self.env['ir.config_parameter'].get_param('production_server.production_server_address')
        if production_server:
            if production_server in os.popen("cat /etc/network/interfaces | grep address","r").read()[8:]:
                return True
        return False
    

class ProductionServerConfiguration(models.TransientModel):
    _inherit = 'base.config.settings'

    production_server_address = fields.Char(string='Production Server Address')
    
    @api.multi
    def get_default_production_server_address(self):
        
        production_address = self.env['ir.config_parameter'].get_param('production_server.production.server.address')
        return {'production_server_address' : production_address}

    @api.multi
    def set_production_server_address(self):
        self.env['ir.config_parameter'].set_param('production_server.production.server.address',self.production_server_address)
        