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

from openerp import models, api,registry

class procurement_order(models.Model):
    _inherit = "procurement.order"
    
    def _run_thread(self,autocommit=False,ids=None):
        with api.Environment.manage():
            with registry(self.env.cr.dbname).cursor() as new_cr:
                new_env = api.Environment(new_cr, self.env.uid, self.env.context)
                try:
                    super(procurement_order,self).with_env(new_env).with_context(from_thread=True).run(autocommit)
                finally:
                    try:                
                        new_env.cr.commit()
                    except Exception:
                        try:           
                            new_env.cr.close()
                        except Exception:
                            pass

    @api.multi
    def run(self, autocommit=False):
        
        thread_run = Thread(target=self._run_thread, args=(autocommit,self._ids))
        thread_run.start()
        
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
