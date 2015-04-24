from openerp import models, fields, api


class purchase_order_type(models.Model):
    _name = 'purchase.order.type'
    
    name = fields.Char('Name',size=255,translate=True,required=True)
    

purchase_order_type()

class purchase_order(models.Model):
    
    _inherit='purchase.order'
    
    purchase_type_id = fields.Many2one('purchase.order.type','Purchase Type')
    
purchase_order()