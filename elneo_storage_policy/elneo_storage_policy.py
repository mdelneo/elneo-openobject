'''
Created on 10 juil. 2012

@author: cth
'''
from datetime import datetime, timedelta
from openerp import models, fields, api
from openerp.osv.fields import related

class procurement_order(models.Model):
    _inherit = 'procurement.order'
    
    def use_procure_method(self, procurement, procure_method, remaining_qty):
        res = super(procurement_order, self).use_procure_method(procurement, procure_method, remaining_qty)
        if not res:
            return res
        if procurement.product_id:
            #find good warehouse detail
            warehouse_detail = None
            for detail in procurement.product_id.warehouse_detail:
                if detail.warehouse_id.id == procurement.rule_id.warehouse_id.id:
                    warehouse_detail = detail
            if not warehouse_detail:
                return res
            
            #check storage policy
            if warehouse_detail.storage_policy in ([policy.name for policy in procure_method.storage_policies]):
                return True
            else:
                return False
        return res
         
             
    
procurement_order()

class procurement_rule_procure_method(models.Model):
    _inherit = 'procurement.rule.procure.method'
    
    storage_policies = fields.One2many('procurement.rule.procure.method.storage.policy', 'procure_method_id', string='Storage policies')
    
procurement_rule_procure_method()

class procurement_rule_procure_method_storage_policy(models.Model):
    _name = 'procurement.rule.procure.method.storage.policy'
    
    procure_method_id = fields.Many2one('procurement.rule.procure.method', 'Procure method')
    name = fields.Selection([('stocked', 'Stocked'),('not_stocked','Not stocked'),('downgraded','Downgraded'),('drop','Drop')], string='Storage policy')
    
procurement_rule_procure_method_storage_policy()    

class product_warehouse_detail(models.Model):
    _name = 'product.warehouse.detail'
    
    @api.one
    def compute_storage_policy(self):
        if len([o.id for o in self.product_tmpl_id.orderpoints if self.warehouse_id.id == o.warehouse_id.id]) > 0:
            self.storage_policy = 'stocked'
        elif self.depreciation_policy == 'not_downgraded':
            self.storage_policy = 'not_stocked'
        elif self.depreciation_policy == 'downgraded':
            self.storage_policy = 'downgraded'
        elif self.depreciation_policy == 'drop':
            self.storage_policy = 'drop'
        else:
            self.storage_policy = None

    @api.one
    def compute_stock(self):
        if self.product_tmpl_id.id:
            self.stock_real = self.product_tmpl_id.with_context({'location':self.warehouse_id.lot_stock_id.id})._product_available(None, False)[self.product_tmpl_id.id]['qty_available']
            self.stock_virtual = self.product_tmpl_id.with_context({'location':self.warehouse_id.lot_stock_id.id})._product_available(None, False)[self.product_tmpl_id.id]['virtual_available']
    
    product_tmpl_id = fields.Many2one('product.template', string='Product', ondelete='cascade')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    stock_real = fields.Float('Real stock', compute='compute_stock')
    stock_virtual = fields.Float('Virtual stock', compute='compute_stock')
    aisle = fields.Char('Aisle')
    storage_policy = fields.Selection([('stocked', 'Stocked'),('not_stocked','Not stocked'),('downgraded','Downgraded'),('drop','Drop')], string='Storage policy', compute='compute_storage_policy')
    depreciation_policy = fields.Selection([('not_downgraded', 'Not downgraded'), ('downgraded', 'Downgraded'), ('drop', 'Drop')], string='Depreciation policy', default='not_downgraded')
    warehouse_description = fields.Text('Warehouse description')
    
product_warehouse_detail()   

class product_product(models.Model):
    _inherit = 'product.product'
    
product_product()

class stock_warehouse_orderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'
    
    product_tmpl_id = fields.Many2one('product.template', related='product_id.product_tmpl_id', store=True)
    
stock_warehouse_orderpoint()

class product_template(models.Model):
    _inherit = 'product.template'
    
    @api.model
    def _get_default_warehouse_detail(self):
        res = []
        for warehouse in self.env['stock.warehouse'].search([]):
            res.append({'warehouse_id':warehouse.id})
        return res
        
    
    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default['barcode_number'] = self.pool.get('ir.sequence').get(cr, uid, 'product.barcode')
        return super(product_template,self).copy(cr, uid, id, default=default, context=context)
    barcode_number = fields.Char('Barcode number', size=7, default=lambda obj: obj.env['ir.sequence'].get('product.barcode'))
    warehouse_detail = fields.One2many('product.warehouse.detail', 'product_tmpl_id', 'Warehouse detail', default=_get_default_warehouse_detail)
    orderpoints = fields.One2many('stock.warehouse.orderpoint', 'product_tmpl_id', 'Minimum Inventory Rules')
    
    
product_template()