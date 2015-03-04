# -*- coding: utf-8 -*-
from openerp import models,fields,api

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    def _get_default_is_company(self):
        return self._context.get('force_is_company', False)
        
    is_company = fields.Boolean('Is a company', default=_get_default_is_company)
    
