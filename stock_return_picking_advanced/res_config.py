from openerp import fields, models, api
#from openerp.tools.safe_eval import safe_eval

class stock_config_settings(models.TransientModel):
    _inherit = 'stock.config.settings'

    
    
    return_valid_auto = fields.Boolean('Validate automatically return pickings',help="When choosing to return products on picking form and after having validated the wizard, picking return is automatically validated.")
    return_create_invoice = fields.Boolean('Create automatically draft invoice after return (if applicable)',help="After having validated return picking and if picking validating auto is enabled, a draft invoice is created")
   

    @api.multi
    def set_default_return_valid_auto(self):
        self.env['ir.config_parameter'].set_param('stock_return_picking_advanced.return_valid_auto',repr(self.return_valid_auto))
        return True
        
    
    @api.model
    def get_default_return_valid_auto(self,fields):
        return_valid_auto = self.env['ir.config_parameter'].get_param('stock_return_picking_advanced.return_valid_auto',False)
        if return_valid_auto =="False":
            return_valid_auto = False
        else:
            return_valid_auto = True
        return {'return_valid_auto':return_valid_auto}
    
    @api.multi
    def set_default_return_create_invoice(self):
        self.env['ir.config_parameter'].set_param('stock_return_picking_advanced.return_create_invoice',repr(self.return_create_invoice))
        return True
        
    
    @api.model
    def get_default_return_create_invoice(self,fields):
        return_create_invoice = self.env['ir.config_parameter'].get_param('stock_return_picking_advanced.return_create_invoice',False)
        if return_create_invoice == "False":
            return_create_invoice = False
        else:
            return_create_invoice = True
        return {'return_create_invoice':return_create_invoice}
    
    @api.onchange('return_valid_auto')
    def _onchange_return_valid_auto(self):
        if not self.return_valid_auto:
            self.return_create_invoice=False
            self.env['ir.config_parameter'].set_param('stock_return_picking_advanced.return_create_invoice',repr(False))
        

