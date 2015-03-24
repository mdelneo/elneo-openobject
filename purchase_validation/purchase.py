
from openerp import models, fields

class purchase_order(models.Model):
    _inherit = 'purchase.order'
    
    validated = fields.Boolean("Validated")

purchase_order()
