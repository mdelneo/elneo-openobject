from datetime import datetime, timedelta
from openerp import models, fields


class product_supplierinfo(models.Model):
    
    _inherit='product.supplierinfo'
    
    last_price_update_date = fields.Datetime('Last Price Update Date',readonly=True)
    last_supplier_price_update = fields.Many2one('elneo.supplier.price.update','Update',readonly=True)
