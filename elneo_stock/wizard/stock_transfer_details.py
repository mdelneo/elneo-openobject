from openerp import models, api, fields


class stock_transfer_details_items(models.TransientModel):
    _inherit = 'stock.transfer_details_items'
    
    initial_quantity = fields.Float('Initial quantity')
    supplier_code = fields.Char('Supplier code')
            
            
class stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'
    
    change_quantity = fields.Selection([('reset_to_zero','Reset to zero'),('reset_init', 'Reset initial quantities')], 'Change quantity')
    
    @api.one
    @api.onchange('change_quantity')
    def onchange_change_quantity(self):
        if self.change_quantity == 'reset_to_zero':
            for item in self.item_ids:
                item.quantity = 0
        else:
            for item in self.item_ids:
                item.quantity = item.initial_quantity
    
    @api.model
    def default_get(self, fields):
        res = super(stock_transfer_details, self).default_get(fields)
        if 'item_ids' in fields:
            picking = self.env['stock.picking'].browse(self._context.get('active_ids'))
            supplier = picking.partner_id
            for item in res['item_ids']:
                if item['product_id']:
                    for suppinfo in self.env['product.product'].browse(item['product_id']).seller_ids:
                        if suppinfo.name and suppinfo.name.id ==  supplier.id:
                            item['supplier_code'] = suppinfo.product_code
                item['initial_quantity'] = item['quantity']
        return res
  