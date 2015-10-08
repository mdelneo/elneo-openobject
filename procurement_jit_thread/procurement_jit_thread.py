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

from openerp import models, api, sql_db

class procurement_order(models.Model):
    _inherit = "procurement.order"
    
    def _run_thread(self,autocommit=False,ids=None):
        cr2 = sql_db.db_connect(self.env.cr.dbname).cursor()
        
        
        uid, context = self.env.uid, self.env.context
        with api.Environment.manage():
            self.env = api.Environment(cr2, uid, context)
            try:
               
                self.env['procurement.order'].run(autocommit)
            finally:
                try:                
                    cr2.commit()
                except Exception:
                    pass
                try:                
                    cr2.close()
                except Exception:
                    pass

    @api.multi
    def run(self, autocommit=False):
        self.env.cr.commit();
        thread_run = Thread(target=self._run_thread, args=({'autocommit':autocommit}))
        thread_run.start()
        
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
