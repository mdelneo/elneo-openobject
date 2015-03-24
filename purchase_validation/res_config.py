from openerp import fields, models, api
from openerp.tools.safe_eval import safe_eval

class res_config(models.TransientModel):
    _name= 'purchase.validation.settings'
    _inherit = 'res.config.settings'
    
    email_template_id=fields.Many2one('email.template','Email Template')
    
    
    @api.multi
    def set_email_template_id(self):
        
        self.env['ir.config_parameter'].set_param('purchase_validation.email_template_id',repr(self.email_template_id.id))
        
        
    @api.multi
    def get_default_email_template_id(self):
        res = {}
        id = safe_eval(self.env['ir.config_parameter'].get_param('purchase_validation.email_template_id','False'))
        if id:
            res.update({'email_template_id':id})
       
        return res

res_config()