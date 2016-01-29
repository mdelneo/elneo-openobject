from openerp import models, fields, api


class PurchaseOrder(models.Model):
    _name='purchase.order'
    _inherit = ['purchase.order','edi.thread','edi.export']
    
    def get_edi_messages(self):
        return super(PurchaseOrder,self).get_edi_messages()
    
    @api.one
    def _get_edi_values(self):
        res = super(PurchaseOrder,self)._get_edi_values
        
        
        res.update()
    
    @api.multi
    def action_confirm(self):
        res = super(PurchaseOrder,self).action_confirm()
        
        self.edi_simple_create()
        
        return res
        
        