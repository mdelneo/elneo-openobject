from openerp import fields, models, api
#from openerp.tools.safe_eval import safe_eval

class base_config_settings(models.TransientModel):
    _inherit = 'sale.config.settings'

    default_route_shop_sale = fields.Many2one('stock.location.route',string='Default route (shop sale)',help='The Default Route proposed on new sale order line for shop sale')
   
    @api.multi
    def set_sale_default_route_shop_sale(self):
        self.env['ir.config_parameter'].set_param('sale_default_route_shop_sale.default_route_shop_sale',repr(self.default_route_shop_sale.id))
        
    
    @api.model
    def get_default_route_shop_sale(self,fields):
        default_route_shop_sale = self.env['ir.config_parameter'].get_param('sale_default_route_shop_sale.default_route_shop_sale',False)
        if default_route_shop_sale !='False':
            default_route_shop_sale = int(default_route_shop_sale)
        else:
            default_route_shop_sale = False
        return {'default_route_shop_sale':default_route_shop_sale}

    
