from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.exceptions import Warning


class sale_delete_line_wizard(models.TransientModel):
    _name = 'sale.delete.line.wizard'
    
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale Order Line',readonly=True)
    purchase_order_line=fields.Many2one('purchase.order.line',string='Purchase Order Line',readonly=True)
    purchase_order=fields.Many2one('purchase.order',string='Purchase Order Line',related='purchase_order_line.order_id',readonly=True)
    stock_move_ids = fields.Many2many('stock.move','sale_delete_line_wizard_stock_rel','wizard_id','move_id',readonly=True)
    
    @api.model
    def default_get(self,fields):
        """
         To get default values for the object.
         @param fields: List of fields for which we want default values
         @return: A dictionary with default values for all field in ``fields``
        """
    
        res = super(sale_delete_line_wizard, self).default_get(fields)
        
        order_line = self.env['sale.order.line'].browse(self.env.context.get('active_id',False))
        
        if order_line:
            moves = order_line.get_moves()
            purchase_order_line = order_line.get_purchase_order_line()
            res.update({'sale_order_line_id':order_line.id,'purchase_order_line':purchase_order_line.id,'stock_move_ids':moves.mapped('id')})
        
        return res
    
    @api.multi
    def delete_line(self):
        for wizard in self:
            #delete purchase order line only if quantity is the same
            if wizard.sale_order_line_id.get_purchase_order_line().product_qty == wizard.sale_order_line_id.product_uom_qty:
                wizard.sale_order_line_id.get_purchase_order_line().force_delete()
            wizard.sale_order_line_id.get_procurements().force_delete()
            wizard.sale_order_line_id.get_moves().force_delete()
            wizard.sale_order_line_id.force_delete()
            wizard.sale_order_line_id.order_id.signal_workflow('ship_corrected')
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
            

class sale_change_quantity_wizard(models.TransientModel):
    _name = 'sale.change.quantity.wizard'
    
    new_quantity = fields.Float(string="New quantity")
    old_quantity = fields.Float(string="Old quantity")
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale Order Line',readonly=True)
    purchase_order_line=fields.Many2one('purchase.order.line',string='Purchase Order Line',readonly=True)
    purchase_order=fields.Many2one('purchase.order',string='Purchase Order Line',related='purchase_order_line.order_id',readonly=True)
    stock_move_ids = fields.Many2many('stock.move','sale_correction_wizard_stock_rel','wizard_id','move_id',readonly=True)
    
    @api.model
    def default_get(self,fields):
        """
         To get default values for the object.
         @param fields: List of fields for which we want default values
         @return: A dictionary with default values for all field in ``fields``
        """
    
        res = super(sale_change_quantity_wizard, self).default_get(fields)
        
        order_line = self.env['sale.order.line'].browse(self.env.context.get('active_id',False))
        
        if order_line:
            moves = self.env['stock.move'].search([('procurement_id.sale_line_id','=',order_line.id)])
            purchase_order_line = order_line.get_purchase_order_line()
            res.update({'sale_order_line_id':order_line.id,'purchase_order_line':purchase_order_line.id,'old_quantity':order_line.product_uom_qty,'new_quantity':order_line.product_uom_qty,'stock_move_ids':moves.mapped('id')})
        
        return res


    @api.multi
    def change_quantity(self):
        for wizard in self:
            if wizard.sale_order_line_id.state != 'confirmed':
                raise Warning(_('You can only apply that modification on "confirmed" order lines.'))
            else:
                sale_line = wizard.sale_order_line_id
                new_quantity = wizard.new_quantity
                old_quantity = wizard.old_quantity
                 
                sale_line.product_uom_qty = new_quantity
                sale_line.product_uos_qty = new_quantity

                #find procurements of order line and change their quantities
                procurements = sale_line.get_procurements()
                for procurement in procurements:
                    procurement.sudo().write({'product_qty':new_quantity, 'product_uos_qty':new_quantity})
            
                
                stock_moves = sale_line.get_moves()
                #if a stock move is available, we only need to add to its quantity, the differences between old and new quantity
                for move in stock_moves:
                    if move.state != 'done':
                        move.product_uom_qty = new_quantity
                        move.product_uos_qty = new_quantity
                
       
        return {'type': 'ir.actions.act_window_close'}