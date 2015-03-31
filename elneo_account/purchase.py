from openerp import models, fields

class purchase_order(models.Model):
    _inherit = 'purchase.order'
    
    partner_vat=fields.Char('Partner VAT',related='partner_id.vat',readonly=True,store=False)

purchase_order()