# -*- coding: utf-8 -*-
from openerp import models,fields,api
from openerp.exceptions import ValidationError

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    ref = fields.Char('Reference', size=10,index=True)
    
    alias = fields.Char('Alias', size=255,index=True)
    
    @api.constrains('ref')
    def _check_ref(self):
        #Mother companies must have reference
        if (not self.parent_id and not self.ref):
            raise ValidationError("You must fill in the reference for this partner!")
        
        sames = self.search([('active','=',True),('parent_id','=',False),('ref','=',self.ref),('id','!=',self.id)])
        if (sames):
            raise ValidationError("There is partner with the same reference! Please change it or go to the good partner.\n\n%s" % (sames[0].name))
            
    def _get_default_is_company(self):
        return self._context.get('force_is_company', False)
        
    is_company = fields.Boolean('Is a company', default=_get_default_is_company)