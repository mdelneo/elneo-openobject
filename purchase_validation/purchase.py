
from openerp import models, fields

class purchase_order(models.Model):
    _inherit = 'purchase.order'
    
    validated = fields.Boolean("Validated",track_visibility='onchange')
    date_validation = fields.Date('Validation date')
    
    _track = {
        'validated': {
            'mt_purchase_validated': lambda self, cr, uid, obj, ctx=None: obj.validated == True,
           
        }}

purchase_order()