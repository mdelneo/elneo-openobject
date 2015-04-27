from openerp import models, fields, api


class stock_warehouse(models.Model):
    _inherit = 'stock.warehouse'
    
    group_id = fields.Many2one('res.groups', string="Group")
    
