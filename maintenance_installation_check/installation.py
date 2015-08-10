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
from openerp import models, fields, api

class maintenance_intervention_product(models.Model):
    _inherit = 'maintenance.installation'
    
    @api.one
    def action_check_installation(self):        
        self.last_verification_date = datetime.now()
        self.last_verification_uid = self.env.user
        
    @api.one
    def _get_verified(self):
        if ((not self.last_verification_date) and (self.last_verification_date < (datetime.today()-timedelta(days=365)).strftime('%Y-%m-%d'))):
            self.is_verified = False
        else:
            self.is_verified=True
 
    
    last_verification_date = fields.Datetime('Last Verification Date',readonly=True)
    last_verification_uid = fields.Many2one('res.users',string="Last Verification User",readonly=True)
    is_verified = fields.Boolean(compute=_get_verified,string='Is Verified',readonly=True)