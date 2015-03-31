from openerp import models, fields

class sale_order(models.Model):
    _inherit='sale.order'
    
    partner_vat=fields.Char('Partner VAT',related='partner_id.vat',readonly=True,store=False)
    
sale_order()    