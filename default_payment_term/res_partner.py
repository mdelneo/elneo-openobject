from openerp import models, fields, api

class res_partner(models.Model):
    
    _inherit = 'res.partner'
   
    @api.model
    def create(self,vals):
        
        if vals and vals.has_key('customer') and vals['customer']:
            term = self.env['ir.config_parameter'].get_param('default_payment_term.payment_term_customer')
            if term :
                vals['property_payment_term']= int(term)
        
        else:
            term = self.env['ir.config_parameter'].get_param('default_payment_term.payment_term_partner')
            if term :
                vals['property_payment_term']= int(term)
            
        return super(res_partner, self).create(vals)
    
    
    @api.onchange('customer')
    def onchange_customer(self):
        if self.customer:
            term = self.env['ir.config_parameter'].get_param('default_payment_term.payment_term_customer')
            if term :
                self.property_payment_term = int(term)
        else:
            term = self.env['ir.config_parameter'].get_param('default_payment_term.payment_term_partner')
            if term :
                self.property_payment_term = int(term)
                
    
res_partner()