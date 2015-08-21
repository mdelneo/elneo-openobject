from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
from openerp import models,fields,api
from operator import itemgetter
import re
from openerp.tools.translate import _

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    @api.multi
    def open_global_discount_wizard(self):
        
        wizard_id = self.env['sale.global.discount.wizard'].create({}).id
        
        return {
            'name':_("Global discount"),
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'sale.global.discount.wizard',
            'res_id': wizard_id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
        }