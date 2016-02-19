# -*- encoding: utf-8 -*-
from openerp import models, api, _
from openerp.exceptions import Warning

class res_partner(models.Model):
    _inherit = "res.partner"

    @api.one
    @api.constrains('vat')
    def check_vat_unique(self):
        # We enter function if self = commercial_partner_id for PERFORMANCE REASONS => vat = commercial field
        # as many function call as there are children in partner
        if not self.vat or self.parent_id:
            return True

        parent = self
        while parent.parent_id:
            parent = parent.parent_id
        
        same_vat_companies = self.search([('vat','=',self.vat),
                    ('id','!=',self.commercial_partner_id.id),
                    ('id','!=',self.id),# In the CREATE case - commercial_partner_id is not set
                     ('parent_id','=',False),
                     ('company_id', '=', self.company_id.id)])
        
        related_companies = self.search([('id','child_of',parent.id),
                                         ('company_id','=',self.company_id.id)])
        
        found_companies = same_vat_companies - related_companies

        if found_companies:
            raise Warning(_(
                    'Partner vat must be unique per company. Partners with same vat and not related, are: %s!') % (', '.join(x.name for x in found_companies if found_companies.name)))
        
        return True    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
