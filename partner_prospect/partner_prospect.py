from openerp import models, api, fields
from openerp.exceptions import ValidationError
from openerp.tools.translate import _

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    CUSTOMER_PROSPECT_SELECTION = [('customer','Customer'),('prospect','Prospect'),('no','None')]
    
    prospect = fields.Boolean('Prospect')
    customer_prospect = fields.Selection(CUSTOMER_PROSPECT_SELECTION, string='Customer relation type', compute='_get_customer_prospect', inverse='_set_customer_prospect', default='prospect')

    
    @api.one
    @api.constrains('customer_prospect', 'is_company','prospect','customer')
    def _check_customer_prospect(self):
        if self.is_company and not self.customer_prospect:
            raise ValidationError(_('Please set customer relation type of the company (customer / prospect).'))
    
    def _commercial_fields(self, cr, uid, context=None):
        return super(res_partner, self)._commercial_fields(cr, uid, context=context) + ['prospect']
    
    def _get_customer_prospect(self):
        for partner in self:
            if partner.is_company:
                if partner.customer:
                    partner.customer_prospect = 'customer'
                elif partner.prospect:
                    partner.customer_prospect = 'prospect'
                else:
                    partner.customer_prospect = 'no'
    
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
        
    