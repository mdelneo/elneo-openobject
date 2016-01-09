from openerp import fields, models, api
#from openerp.tools.safe_eval import safe_eval

class stock_config_settings(models.TransientModel):
    _inherit = 'stock.config.settings'

    po_for_orderpoints = fields.Boolean('Create separate Purchase Order for Orderpoints',help="When procurements for restocking are launched, use purchase orders that are not linked to Sales Orders.")

    @api.multi
    def set_default_po_for_orderpoints(self):
        self.env['ir.config_parameter'].set_param('orderpoint_purchase_unique.po_for_orderpoints',repr(self.po_for_orderpoints))
        return True
        
    
    @api.model
    def get_default_po_for_orderpoints(self,fields):
        unique = self.env['ir.config_parameter'].get_param('orderpoint_purchase_unique.po_for_orderpoints',False)
        if unique =="False":
            unique = False
        else:
            unique = True
        return {'po_for_orderpoints':unique}