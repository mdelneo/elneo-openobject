from openerp import models, fields, netsvc, api

class purchase_order(models.Model):
    _inherit = 'purchase.order'

    @api.one
    def purchase_confirm_elneo(self):
        
        
        
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate('purchase.order', self.id, 'purchase_confirm')
        
        
        return True

purchase_order()