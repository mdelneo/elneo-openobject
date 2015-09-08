from openerp import models, fields, api

class base_config_settings(models.TransientModel):
    _inherit = 'purchase.config.settings'

    default_purchase_type_id = fields.Many2one('purchase.order.type',string='Default purchase type',help='The Default purchase type proposed on new sale purchase order')
   
    @api.multi
    def set_purchase_default_purchase_type(self):
        self.env['ir.config_parameter'].set_param('elneo_purchase.default_purchase_type_id',repr(self.default_purchase_type_id.id))
        
    @api.model
    def get_default_purchase_type_id(self,fields):
        default_purchase_type_id = self.env['ir.config_parameter'].get_param('elneo_purchase.default_purchase_type_id',False)
        if default_purchase_type_id !='False':
            default_purchase_type_id = int(default_purchase_type_id)
        else:
            default_purchase_type_id = False
        return {'default_purchase_type_id':default_purchase_type_id}

class purchase_order_type(models.Model):
    _name = 'purchase.order.type'
    
    name = fields.Char('Name',size=255,translate=True,required=True)


class purchase_order(models.Model):
    
    _inherit='purchase.order'
    
    purchase_type_id = fields.Many2one('purchase.order.type','Purchase Type')
    
    @api.model
    def default_get(self, fields_list):
        res = super(purchase_order,self).default_get(fields_list)
        purchase_type = self.env['ir.config_parameter'].get_param('elneo_purchase.default_purchase_type_id',False)
        if purchase_type:
            purchase_type_id = int(purchase_type)
            res['purchase_type_id'] = purchase_type_id
        return res