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
from threading import Thread
import logging
import time

from openerp import models, api,registry

class procurement_order(models.Model):
    _inherit = "procurement.order"
    
    @api.multi
    def run(self, autocommit=False):
        for procurement in self:
            if procurement.sale_line_id and procurement.sale_line_id.order_id and procurement.sale_line_id.order_id.shop_sale:
                #simulate from_thread if come from a shop_sale
                super(procurement_order,self.with_context(from_thread=True)).run(autocommit)
            else:
                super(procurement_order,self.with_context(from_thread=False)).run(autocommit)
        return True

