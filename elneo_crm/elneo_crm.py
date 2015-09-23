# -*- coding: utf-8 -*-
from openerp import models,fields,api

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    ref = fields.Char('Reference', size=10,select=1)
    
    alias = fields.Char('Alias', size=255,select=1)
    
    
    def init(self,cr):
        #UPDATE DATABASE TO AVOID NULL PROBLEMS
        query="UPDATE res_partner SET ref = 'TO CORRECT' WHERE ref IS NULL"
        
        cr.execute(query)
        
    @api.model
    def create(self,vals):
        
        if not vals.get('ref') or vals.get('ref') == '':
            vals.update({'ref': 'TO CORRECT'})
        
        partner = super(res_partner,self).create(vals)
        
        return partner
           
    
    def _get_default_is_company(self):
        return self._context.get('force_is_company', False)
        
    is_company = fields.Boolean('Is a company', default=_get_default_is_company)

res_partner()