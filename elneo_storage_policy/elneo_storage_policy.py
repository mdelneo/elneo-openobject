'''
Created on 10 juil. 2012

@author: cth
'''
from datetime import datetime, timedelta
from openerp import models, fields, api


class product_warehouse_detail(models.Model):
    _name = 'product.warehouse.detail'
    
    def compute_storage_policy(self):
        result = {}    
        for detail in self:
            result[detail.id] = {}
            if len([o.id for o in detail.product_id.orderpoints if detail.warehouse_id.id == o.warehouse_id.id]) > 0:
                result[detail.id]['storage_policy'] = 'stocked'
            elif detail.depreciation_policy == 'not_downgraded':
                result[detail.id]['storage_policy'] = 'not_stocked'
            elif detail.depreciation_policy == 'downgraded':
                result[detail.id]['storage_policy'] = 'downgraded'
            elif detail.depreciation_policy == 'drop':
                result[detail.id]['storage_policy'] = 'drop'
            else:
                result[detail.id]['storage_policy'] = None
            return result
        
    def compute_stock(self):
        self.stock_real = 0
        self.stock_virtual = 0
    
    product_id = fields.Many2one('product.template', string='Product')
    warehouse_id = fields.Many2one('stock.warehouse')
    stock_real = fields.Float('Real stock', compute='compute_stock')
    stock_virtual = fields.Float('Virtual stock', compute='compute_stock')
    aisle = fields.Char('Aisle')
    storage_policy = fields.Selection([('stocked', 'Stocked'),('not_stocked','Not stocked'),('downgraded','Downgraded'),('drop','Drop')], string='Storage policy', compute='compute_storage_policy')
    depreciation_policy = fields.Selection([('not_downgraded', 'Not downgraded'), ('downgraded', 'Downgraded'), ('drop', 'Drop')], string='Depreciation policy', default='not_downgraded')
    warehouse_description = fields.Text('Warehouse description')
product_warehouse_detail()   

class product_template(models.Model):
    _inherit = 'product.template'
    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default['barcode_number'] = self.pool.get('ir.sequence').get(cr, uid, 'product.barcode')
        return super(product_template,self).copy(cr, uid, id, default=default, context=context)
    barcode_number = fields.Char('Barcode number', size=7, default=lambda obj: obj.env['ir.sequence'].get('product.barcode'))
    warehouse_detail = fields.One2many('product.warehouse.detail', 'product_id', 'Warehouse detail')
    orderpoints = fields.One2many('stock.warehouse.orderpoint', 'product_id', 'Minimum Inventory Rules')
product_template()