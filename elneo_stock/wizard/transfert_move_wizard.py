from openerp import models, api, fields


class transfert_move_wizard(models.TransientModel):
    
    _name = 'transfert.move.wizard'
    
    move_id = fields.Many2one('stock.move', 'Stock move')
    product_id = fields.Many2one('product.product', 'Product')
    quantity = fields.Float('Quantity')
    
    @api.model
    def default_get(self, fields_list):
        res = super(transfert_move_wizard, self).default_get(fields_list)
        if not res:
            res = {}
        move_id = self._context.get('active_id',False)
        if move_id:
            move = self.env['stock.move'].browse(move_id)
            res['move_id'] = move_id
            if move.product_id:
                res['product_id'] = move.product_id.id
            if move.product_uom_qty:
                res['quantity'] = move.product_uom_qty
            elif move.product_uos_qty:
                res['quantity'] = move.product_uos_qty
        return res
    @api.multi
    def do_transfert(self):
        move = self.move_id
        remaining_qty = move.product_uom_qty-self.quantity
        new_move_id = move.split(move, remaining_qty)
        move.product_uom_qty = self.quantity
        move.product_uos_qty = self.quantity
        move.action_done()
        if new_move_id != move.id:
            self.env['stock.move'].browse(new_move_id).action_assign()
        return True
      