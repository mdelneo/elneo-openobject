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
        self.move_id.product_uom_qty = self.quantity
        self.move_id.product_uos_qty = self.quantity
        self.move_id.action_done()
        
        '''
        processed_ids = []
        pack_datas = {
            'product_id': self.product_id.id,
            'product_uom_id': self.move_id.product_uom_id.id,
            'product_qty': self.quantity,
            'package_id': self.move_id.package_id.id,
            'lot_id': self.move_id.lot_id.id,
            'location_id': self.move_id.sourceloc_id.id,
            'location_dest_id': self.move_id.destinationloc_id.id,
            'result_package_id': self.move_id.result_package_id.id,
            'date': datetime.now(),
        }
        pack_datas['picking_id'] = self.move_id.picking_id.id
        packop_id = self.env['stock.pack.operation'].create(pack_datas)
        processed_ids.append(packop_id.id)
            

        # Execute the transfer of the picking
        self.picking_id.do_transfer()
        '''
    
        return True