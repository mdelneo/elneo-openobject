from openerp import models, fields, api

class PurchaseOrder(models.Model):
    _name='purchase.order'
    _inherit = ['purchase.order','edi.export']
 
    @api.one
    def simple_edi_export(self):
        res = super(PurchaseOrder,self).simple_edi_export()
        
        if self.env.context.get('edi_landefeld',False):
            wizard = self.env['landefeld.edi.export'].create({'purchase_id':self.id})
            wizard._export()
        else:       
            res = super(PurchaseOrder,self).simple_edi_export()
        
        return res
    
    @api.multi
    def button_simple_edi_export(self):
        for order in self.filtered(lambda r:r.partner_id.id==self.env['product.product'].LANDEFELD_PARTNER_ID):
            order.with_context(edi_landefeld=True).simple_edi_export()
        
        return super(PurchaseOrder,self).button_simple_edi_export()