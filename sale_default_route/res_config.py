from openerp import fields, models, api
#from openerp.tools.safe_eval import safe_eval

class base_config_settings(models.TransientModel):
    _inherit = 'sale.config.settings'

    default_route = fields.Many2one('stock.location.route',string='Default Route',help='The Default Route proposed on new sale order line')
   
    @api.multi
    def set_sale_default_route_stock(self):
        self.env['ir.config_parameter'].set_param('sale_default_route.default_route',repr(self.default_route.id))
        
    
    @api.model
    def get_default_route(self,fields):
        default_route = self.env['ir.config_parameter'].get_param('sale_default_route.default_route',False)
        if default_route !='False':
            default_route = int(default_route)
        else:
            default_route = False
        return {'default_route':default_route}

