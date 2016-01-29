from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.exceptions import Warning


class sale_delete_line_wizard(models.TransientModel):
    _name = 'sale.delete.line.wizard'
    
    @api.model
    def _get_sale_order_line_id(self):
        self.sale_order_line_id = self.env.context.get('active_id')
    
    sale_order_line_id = fields.Many2one('sale.order.line', 'Sale Order',default=_get_sale_order_line_id)
    #stock_move_ids = fields.One2many('stock.move',domain=[('procurement_id.sale_line_id','=',sale_order_line_id.id)], default=_get_moves)
    
    @api.multi
    def delete_line(self):
        sale_order_line_ids = self.env['sale.order.line']
        
        for wizard in self:
            if wizard.sale_order_line_id.state != 'confirmed':
                raise Warning(_('You can only apply that modification on "confirmed" order lines.'))
            sale_order_line_ids += wizard.sale_order_line_id
        
        #delete procurement
        cr.execute('''select procurement_order.id, stock_move.id, stock_move.state, stock_move.product_qty, sale_order_line.id 
            from 
            sale_order_line 
            left join stock_move
            left join procurement_order on procurement_order.move_id = stock_move.id
            on stock_move.sale_line_id = sale_order_line.id 
            where sale_order_line.id in %s and procurement_order.id is not null
            ''', (tuple(sale_order_line_ids),))
            
        request_result = cr.fetchall()
        
        procurement_ids = []
        stock_move_ids = []
        stock_moves_to_copy = {}
        
        for (procurement_id, stock_move_id, move_state, quantity, sale_order_line_id) in request_result:
            if move_state == 'done':
                stock_moves_to_copy[stock_move_id] = -quantity
            else:
                procurement_ids.append(procurement_id)
                stock_move_ids.append(stock_move_id)
            
        self.pool.get("procurement.order").force_delete(cr, uid, procurement_ids, context)
        
        #find moves to delete if move_to_copy
        moves_to_copy = self.pool.get("stock.move").browse(cr, uid, stock_moves_to_copy.keys(), context)
        for move_to_copy in moves_to_copy:
            stock_move_ids.append(move_to_copy.move_dest_id.id)
        
        #delete stock moves
        moves = self.pool.get("stock.move").browse(cr, uid, stock_move_ids, context)
        for move in moves:
            current_move = move
            while current_move.move_dest_id:
                stock_move_ids.append(current_move.move_dest_id.id)
                current_move = current_move.move_dest_id
            
                
        self.pool.get("stock.move").force_delete(cr, uid, stock_move_ids, context)
        self.pool.get('stock.move').copy_stock_moves(cr, uid, stock_moves_to_copy.keys(), stock_moves_to_copy, context)
        
        #delete order line
        self.pool.get("sale.order.line").force_delete(cr, uid, sale_order_line_ids, context)
        
        return {'type': 'ir.actions.act_window_close'}
    
sale_delete_line_wizard()



class sale_change_quantity_wizard(models.TransientModel):
    _name = 'sale.change.quantity.wizard'
    
    
    @api.model
    def default_get(self,fields):
        """
         To get default values for the object.
         @param fields: List of fields for which we want default values
         @return: A dictionary with default values for all field in ``fields``
        """
    
        res = super(sale_change_quantity_wizard, self).default_get(fields)
        
        active_id = self.env.context.get('active_id',False)
        
        order_line = self.env['sale.order.line'].browse(active_id)
        
        if order_line:
            moves = self.env['stock.move'].search([('procurement_id.sale_line_id','=',order_line.id)])
            procurement = self.env['procurement.order'].search([('sale_line_id','=',order_line.id),('purchase_id','!=',False)])
            procurement.ensure_one()
            purchase_line_id = self.env['purchase.order.line']
            if procurement and procurement.purchase_line_id:
                purchase_line_id = procurement.purchase_line_id
            res.update({'sale_order_line_id':order_line.id,'purchase_order_line':purchase_line_id.id,'old_quantity':order_line.product_uom_qty,'new_quantity':order_line.product_uom_qty,'stock_move_ids':moves.mapped('id')})
        
        
                
        return res

    new_quantity = fields.Float(string="New quantity")
    old_quantity = fields.Float(string="Old quantity")
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale Order Line',readonly=True)
    virtual_stock = fields.Float(string='Virtual Stock',readonly=True,)
    purchase_order_line=fields.Many2one('purchase.order.line',string='Purchase Order Line',readonly=True)
    stock_move_ids = fields.Many2many('stock.move','sale_correction_wizard_stock_rel','wizard_id','move_id',readonly=True)

    @api.multi
    def change_quantity(self):
        sale_order_lines = self.env['sale.order.line']
        new_quantities = {}
        old_quantities = {}
        
        for wizard in self:
            if wizard.sale_order_line_id.state != 'confirmed':
                raise Warning(_('You can only apply that modification on "confirmed" order lines.'))
            elif wizard.new_quantity > self.stock_virtual+wizard.old_quantity:
                raise Warning(_('The new quantity must be less than the quantity available in stock after correction (%s)')%str(wizard.stock_virtual+wizard.old_quantity))
            else:
                sale_order_lines += wizard.sale_order_line_id

                new_quantities[wizard.sale_order_line_id.id] = wizard.new_quantity
                old_quantities[wizard.sale_order_line_id.id] = wizard.old_quantity 
                
        self.env['sale.corretion.change.sale'].action_modify_after_confirm_sale_wizard(sale_order_lines,new_quantities,old_quantities)
       
        return {'type': 'ir.actions.act_window_close'}
    
    class SaleCorrectionChangeSale(models.TransientModel):
        _name='sale.correction.change.sale'
        
        def force_delete(self, cr, uid, ids, context=None):
            self.pool.get("sale.order.line").write(cr, uid, ids, {'state':'cancel'} ,context)
            return None
    
        @api.model
        def action_modify_after_confirm_add_notification(self, sale_lines, new_quantities, old_quantities):
    
            for line in sale_lines:
                
                line.order_id.message_post(body=_('Line of product %s quantity modified from %s to %s') % (line.name,str(old_quantities[line.id]),str(new_quantities[line.id])))
                
            return None
    
        @api.model
        def action_modify_after_confirm_sale_wizard(self,sale_lines,new_quantities, old_quantities):
            
            self.action_modify_after_confirm(sale_lines, new_quantities)
            
            #find procurements of order line and change their quantities
            self.env.cr.execute('''select procurement_order.id, sale_order_line.id 
                from 
                sale_order_line 
                left join stock_move
                left join procurement_order on procurement_order.move_id = stock_move.id
                on stock_move.sale_line_id = sale_order_line.id 
                where sale_order_line.id in %s and procurement_order.id is not null
                ''', (tuple(sale_lines._ids),))
                
            request_result = self.env.cr.fetchall()
            new_quantities_for_procurement = dict([(procurement_order_id, new_quantities[sale_order_line_id]) for (procurement_order_id, sale_order_line_id) in request_result])
            self.env['sale.correction.change.procurement'].action_modify_after_confirm(SUPERUSER_ID, new_quantities_for_procurement.keys(), new_quantities_for_procurement)
                
            #find stock moves of order line and change quantities
            self.env.cr.execute('''select stock_move.id, sale_line_id, stock_move.state, product_qty, picking_id, stock_picking.state, stock_picking_type.code
            from stock_move 
            left join stock_picking on stock_move.picking_id = stock_picking.id 
            left join stock_picking_type on stock_picking._picking_type_id
            where sale_line_id in %s''', (tuple(sale_lines._ids),))
            
            request_result = self.env.cr.fetchall()
            
            new_quantities_for_stock_move = {}
            stock_moves_to_copy = {}
            pickings_correction_assigned = self.env['stock.picking'] 
            stock_moves_not_done = {}
            stock_moves_done = {}
            stock_moves_out = self.env['stock.move']
            
            #if a stock move is available, we only need to add to its quantity, the differences between old and new quantity
            for (stock_move_id, sale_order_line_id, move_state, product_qty, picking_id, picking_state, picking_type_code) in request_result:
                if move_state != 'done':
                    stock_moves_not_done[sale_order_line_id, picking_id] = stock_move_id
                    new_quantities_for_stock_move[stock_move_id] = product_qty+(new_quantities[sale_order_line_id]-old_quantities[sale_order_line_id])
                    if picking_type_code == 'outgoing':
                        stock_moves_out+=self.env['stock.move'].browse(stock_move_id)
                    
            #if a stock move is done, we need to create a new move with the difference, ONLY IF NOT ANY OTHER AVAILABLE MOVE FOR THE SAME ORDER LINE EXIST.
            for (stock_move_id, sale_order_line_id, move_state, product_qty, picking_id, picking_state, picking_type_code) in request_result:
                if move_state == 'done': 
                    if not stock_moves_not_done.has_key((sale_order_line_id, picking_id)) and not stock_moves_done.has_key((sale_order_line_id, picking_id)):
                        if picking_state == 'done':
                            pickings_correction_assigned+=self.env['stock.picking'].browse(picking_id) 
                        stock_moves_to_copy[stock_move_id] = new_quantities[sale_order_line_id]-old_quantities[sale_order_line_id]
                    stock_moves_done[sale_order_line_id, picking_id] = stock_move_id
                    if picking_type_code == 'outgoing':
                        stock_moves_out+=self.env['stock.move'].browse(stock_move_id)
            
            self.env['sale.correction.stock.move'].sudo().action_modify_after_confirm(new_quantities_for_stock_move.keys(), new_quantities_for_stock_move)
            self.env['sale.correction.stock.move'].sudo().copy_stock_moves( stock_moves_to_copy.keys(), stock_moves_to_copy)
            stock_moves_out.write({'state':'waiting'})
            
            
            #change the picking state if necessary
            pickings_correction_assigned.signal_workflow('correction')
               
            
            #add a note in sale orders
            self.action_modify_after_confirm_add_notification(sale_lines, new_quantities, old_quantities)
            
            return None
        
        @api.model
        def action_modify_after_confirm(self,sale_lines, new_quantities):
            
            for line in sale_lines:
                line.product_uom_qty = new_quantities[line.id]
            
            return True
        
class SaleCorrectionChangeProcurement(models.TransientModel):
    _name='sale.correction.change.procurement'
    
    @api.model
    def action_modify_after_confirm(self,procurements, new_quantities):
        for procurement in procurements:
            procurement.sudo().write({'product_qty':new_quantities[id], 'product_uos_qty':new_quantities[id]})
        return True
    @api.model
    def force_delete(self, procurements):
       
        for procurement in procurements:
            procurement.delete_workflow()
            procurement.state = 'cancel'

        return True
        
class SaleCorrectionStockMove(models.TransientModel):
    _name='sale.correction.stock.move'
    
    @api.model
    def copy_stock_moves(self, moves, new_stock_moves_quantities):
        for move in moves:
            move.sudo().copy({'product_qty':new_stock_moves_quantities[id], 'product_uos_qty':new_stock_moves_quantities[id], "state":"assigned"})
        return True
    
    @api.model
    def action_modify_after_confirm(self, moves, new_quantities):
        for move in moves:
            move.sudo().write( {'product_qty':new_quantities[id], 'product_uos_qty':new_quantities[id]})
        return None
    
    @api.model
    def force_delete(self, moves):
        moves.state = 'draft'
        moves.unlink()
        
        return True
    