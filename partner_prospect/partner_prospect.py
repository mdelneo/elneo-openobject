from openerp import models, api, fields
from openerp.exceptions import ValidationError
from openerp.tools.translate import _

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    CUSTOMER_PROSPECT_SELECTION = [('customer','Customer'),('prospect','Prospect'),('none','None')]
    
    prospect = fields.Boolean('Prospect')
    
    def _get_customer_prospect(self):
        for partner in self:
            if partner.is_company:
                if partner.customer:
                    partner.customer_prospect = 'customer'
                elif partner.prospect:
                    partner.customer_prospect = 'prospect'
    
    @api.onchange('customer_prospect')
    def _set_customer_prospect(self):
        for partner in self:
            if partner.is_company:
                if partner.customer_prospect == 'customer':
                    partner.customer = True
                    partner.prospect = False
                elif partner.customer_prospect == 'prospect':
                    partner.customer = False
                    partner.prospect = True
                else:
                    partner.customer = False
                    partner.prospect = False
        
    
    customer_prospect = fields.Selection(CUSTOMER_PROSPECT_SELECTION, string='Type', compute='_get_customer_prospect', inverse='_set_customer_prospect')