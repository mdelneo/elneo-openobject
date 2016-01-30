from openerp import models, fields,api


class base_config_settings(models.TransientModel):
    _inherit = 'sale.config.settings'

    landefeld_direct_min_amount = fields.Float(string='Landefeld Direct Min Amount',help='The minimum amount to warn user if he wants to deliver from Landefeld directly')
   
    @api.multi
    def set_sale_default_carrier(self):
        self.env['ir.config_parameter'].set_param('elneo_landefeld.landefeld_direct_min_amount',str(self.landefeld_direct_min_amount))
        
    
    @api.model
    def get_default_carrier(self,fields):
        landefeld_direct_min_amount = self.env['ir.config_parameter'].get_param('elneo_landefeld.landefeld_direct_min_amount',False)
        if landefeld_direct_min_amount !='False':
            landefeld_direct_min_amount = float(landefeld_direct_min_amount)
        else:
            landefeld_direct_min_amount = False
        return {'landefeld_direct_min_amount':landefeld_direct_min_amount}