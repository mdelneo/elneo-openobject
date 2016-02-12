# -*- encoding: utf-8 -*-
from openerp import models, api, _
from openerp.exceptions import Warning


class res_partner(models.Model):
    _inherit = "res.partner"

    @api.one
    @api.constrains('vat', 'parent_id', 'company_id')
    def check_vat_unique(self):
        if not self.vat:
            return True
        
        same_vat_companies = self.search([('vat','=',self.vat),
                    ('id','!=',self.commercial_partner_id.id),
                     ('parent_id','=',False),
                     ('vat','!=',False),
                     ('company_id', '=', self.company_id.id)])
        
        if same_vat_companies:
            raise Warning(_(
                    'Partner vat must be unique per company. Partners with same vat and not related, are: %s!') % (', '.join(x.name for x in same_vat_companies if same_vat_companies.name)))
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
