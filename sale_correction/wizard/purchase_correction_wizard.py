from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.exceptions import Warning


class purchase_delete_line_wizard(models.TransientModel):
    _name = 'purchase.delete.line.wizard'
    
    purchase_order_line_id = fields.Many2one('purchase.order.line', string='purchase Order Line',readonly=True)
    stock_move_ids = fields.Many2many('stock.move','purchase_delete_line_wizard_stock_rel','wizard_id','move_id',readonly=True)
    
    @api.model
    def default_get(self,fields):
        """
         To get default values for the object.
         @param fields: List of fields for which we want default values
         @return: A dictionary with default values for all field in ``fields``
        """
    
        res = super(purchase_delete_line_wizard, self).default_get(fields)
        
        order_line = self.env['purchase.order.line'].browse(self.env.context.get('active_id',False))
        
        if order_line.order_id.state != 'approved':
            raise Warning(_('You can only do modifications on confirmed order.'))
        
        if order_line:
            moves = order_line.get_moves()
            res.update({'purchase_order_line_id':order_line.id,'old_quantity':order_line.product_qty,'new_quantity':order_line.product_qty,'stock_move_ids':moves.mapped('id')})
        
        return res
    
    @api.multi
    def delete_line(self):
        for wizard in self:
            wizard.purchase_order_line_id.get_moves().force_delete()
            wizard.purchase_order_line_id.get_procurements().force_delete()
            wizard.purchase_order_line_id.force_delete()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
            

class purchase_change_quantity_wizard(models.TransientModel):
    _name = 'purchase.change.quantity.wizard'
    
    new_quantity = fields.Float(string="New quantity")
    old_quantity = fields.Float(string="Old quantity")
    purchase_order_line_id = fields.Many2one('purchase.order.line', string='purchase Order Line',readonly=True)
    stock_move_ids = fields.Many2many('stock.move','purchase_correction_wizard_stock_rel','wizard_id','move_id',readonly=True)
    
    @api.model
    def default_get(self,fields):
        """
         To get default values for the object.
         @param fields: List of fields for which we want default values
         @return: A dictionary with default values for all field in ``fields``
        """
    
        res = super(purchase_change_quantity_wizard, self).default_get(fields)
        
        order_line = self.env['purchase.order.line'].browse(self.env.context.get('active_id',False))
        
        if order_line.order_id.state != 'approved':
            raise Warning(_('You can only do modifications on confirmed order.'))
        
        if order_line:
            moves = order_line.get_moves()
            for move in moves:
                if move.state == 'done':
                    raise Warning(_("You can't modify quantity : reception %s is done")%(move.picking_id.name))
            res.update({'purchase_order_line_id':order_line.id,'old_quantity':order_line.product_qty,'new_quantity':order_line.product_qty,'stock_move_ids':moves.mapped('id')})
        
        return res


    @api.multi
    def change_quantity(self):
        for wizard in self:
            if wizard.purchase_order_line_id.state != 'confirmed':
                raise Warning(_('You can only apply that modification on "confirmed" order lines.'))
            else:
                purchase_line = wizard.purchase_order_line_id
                new_quantity = wizard.new_quantity
                old_quantity = wizard.old_quantity
                 
                purchase_line.product_qty = new_quantity
                purchase_line.product_qty = new_quantity

                #find procurements of order line and change their quantities
                procurements = purchase_line.get_procurements()
                for procurement in procurements:
                    procurement.sudo().write({'product_qty':new_quantity, 'product_uos_qty':new_quantity})
            
                
                stock_moves = purchase_line.get_moves()
                #if a stock move is available, we only need to add to its quantity, the differences between old and new quantity
                for move in stock_moves:
                    if move.state != 'done':
                        move.product_uom_qty = new_quantity
                        move.product_uos_qty = new_quantity
                
       
        return {'type': 'ir.actions.act_window_close'}