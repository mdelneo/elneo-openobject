from openerp import fields, models, api
from openerp.tools.safe_eval import safe_eval

class res_config(models.TransientModel):
    _name= 'account.payment.settings'
    _inherit = 'res.config.settings'

    payment_term_partner = fields.Many2one('account.payment.term',string='Partner Default Payment Term',help='The Payment Term used by default for a new Partner (which is not a Customer)')
    
    payment_term_customer = fields.Many2one('account.payment.term',string='Customer Default Payment Term',help='The Payment Term used by default for a new Customer (or for a Partner which becomes a Customer)')
    
    
    @api.multi
    def get_payment_term_partner(self):
        res = {}
        term = self.env['ir.config_parameter'].get_param('payment_term_partner')
        
        res['payment_term_partner'] = term
        
        return res
    
    @api.multi
    def get_default_payment_term_partner(self):
        res = {}
        term = safe_eval(self.env['ir.config_parameter'].get_param('default_payment_term.payment_term_partner','False'))
        if term:
            res.update({'payment_term_partner':term})
        #test = self.payment_term_partner
        
        return res
    
    @api.multi
    def set_payment_term_partner(self):
        
        self.env['ir.config_parameter'].set_param('default_payment_term.payment_term_partner',repr(self.payment_term_partner.id))
      

res_config()