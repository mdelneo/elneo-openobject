from openerp import fields, models, api
#from openerp.tools.safe_eval import safe_eval

class res_config(models.TransientModel):
    _inherit = 'purchase.config.settings'

    purchase_validate_amount = fields.Integer('Amount Validation',default=10000,help='The purchase amount level to block the purchase and wait for validation')
    purchase_validate_group = fields.Many2one('res.groups','Group')
    
    @api.multi
    def set_purchase_validate_amount(self):
        
        self.env['ir.config_parameter'].set_param('elneo_purchase_validate_amount.purchase_validate_amount',repr(self.purchase_validate_amount))
        
    @api.multi
    def set_purchase_validate_group(self):
        
        self.env['ir.config_parameter'].set_param('elneo_purchase_validate_amount.purchase_validate_group',repr(self.purchase_validate_group.id))
        
    
    @api.model
    def get_default_values(self,fields):
        
        purchase_validate_amount = self.env['ir.config_parameter'].get_param('elneo_purchase_validate_amount.purchase_validate_amount',False)
        purchase_validate_group = self.env['ir.config_parameter'].get_param('elneo_purchase_validate_amount.purchase_validate_group',False)

        return {'purchase_validate_amount':int(purchase_validate_amount),
                'purchase_validate_group':int(purchase_validate_group),
                }
      

res_config()