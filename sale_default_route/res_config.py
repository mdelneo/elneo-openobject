from openerp import fields, models, api
#from openerp.tools.safe_eval import safe_eval

class res_config(models.TransientModel):
    _inherit = 'sale.config.settings'

    sale_default_route_stock = fields.Many2one('stock.location.route',string='Default Route on Stock',help='The Default Route proposed if there is enough stock on Sale Order Line')
    
    sale_default_route_no_stock = fields.Many2one('stock.location.route',string='Default Route without Stock',help='The Default Route proposed if there is no stock on Sale Order Line')
    
    
   
    @api.multi
    def set_sale_default_route_stock(self):
        
        self.env['ir.config_parameter'].set_param('sale_default_route.sale_default_route_stock',repr(self.sale_default_route_stock.id))
        
    
    @api.model
    def get_default_values(self,fields):
        
        sale_default_route_stock = self.env['ir.config_parameter'].get_param('sale_default_route.sale_default_route_stock',False)
        
        sale_default_route_no_stock = self.env['ir.config_parameter'].get_param('sale_default_route.sale_default_route_no_stock',False)
        
        if sale_default_route_stock !='False':
            sale_default_route_stock = int(sale_default_route_stock)
        else:
            sale_default_route_stock = False
            
        if sale_default_route_no_stock !='False':
            sale_default_route_no_stock = int(sale_default_route_no_stock)
        else:
            sale_default_route_no_stock = False
        
        
        return {'sale_default_route_stock':sale_default_route_stock,
                'sale_default_route_no_stock':sale_default_route_no_stock
                
                }

    
    
    @api.multi
    def set_sale_default_route_no_stock(self):
        
        self.env['ir.config_parameter'].set_param('sale_default_route.sale_default_route_no_stock',repr(self.sale_default_route_no_stock.id))
      

res_config()