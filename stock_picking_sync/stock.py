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

class StockPicking(models.Model):
    _inherit='stock.picking'
    
    inconsistent_state = fields.Boolean(string='Picking state is not synchronized with moves states.',compute='_get_inconsistent_state')

    @api.multi
    def action_sync(self):
        for picking in self:
            state = picking._state_get(None,None)
            if (state[picking.id]):
                picking.state = state[picking.id]
        return True
    
    
    @api.multi
    def _get_inconsistent_state(self):
        for picking in self:
            state = picking._state_get(None,None)
            if picking.state != state[picking.id]:
                picking.inconsistent_state = True
            else:
                picking.inconsistent_state = False
        
        return True
    