from openerp import fields, models, api
#from openerp.tools.safe_eval import safe_eval

class res_config(models.TransientModel):
    _inherit = 'purchase.config.settings'

    purchase_important_remind_delay = fields.Integer('Days Before Reminder',help='The delay in days before a reminder should be sent to purchase validator to check the purchase delivery delay')
    
    @api.multi
    def set_purchase_important_remind_delay(self):
        
        
        company_email = self.env['res.users'].sudo().browse(self.env.user.id).company_id.email
        
        if not company_email:
            Warning(_('Warning'),_('Company email is not set. Please fill it in before continue.'))
        
        self.env['ir.config_parameter'].set_param('important_purchase.purchase_important_remind_delay',repr(self.purchase_important_remind_delay))
        
    
    @api.model
    def get_default_values(self,fields):
        
        purchase_important_remind_delay = self.env['ir.config_parameter'].get_param('important_purchase.purchase_important_remind_delay',False)

        return {'purchase_important_remind_delay':int(purchase_important_remind_delay),
                
                }
      

res_config()