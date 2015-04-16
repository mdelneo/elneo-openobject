from openerp import models, fields, netsvc, api

class purchase_order(models.Model):
    _inherit = 'purchase.order'

    @api.one
    def elneo_purchase_confirm(self):
        
        
        self.signal_workflow('purchase_confirm')

        return True

purchase_order()