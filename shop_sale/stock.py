from openerp import models, fields


class stock_warehouse(models.Model):
    _inherit = 'stock.warehouse'
    
    
    shop_sale_journal_id = fields.Many2one('account.journal', 'Default Shop Sale Journal')

stock_warehouse()