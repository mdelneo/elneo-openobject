from osv import fields, osv
import decimal_precision as dp
import netsvc

class sale_order(osv.osv):
    
    _name = 'sale.order'
    _inherit = 'sale.order'
    
    def test_state(self, cr, uid, ids, mode, *args):
        assert mode in ('finished', 'canceled'), _("invalid mode for test_state")
        finished = True
        canceled = False
        notcanceled = False
        write_done_ids = []
        write_cancel_ids = []
        for order in self.browse(cr, uid, ids, context={}):
            for line in order.order_line:
                if (not line.procurement_id) or (line.procurement_id.state=='done'):
                    if line.state != 'done' and line.state != 'cancel' : #modified
                        write_done_ids.append(line.id)
                else:
                    finished = False
                if line.procurement_id:
                    if (line.procurement_id.state == 'cancel'):
                        canceled = True
                        if line.state != 'exception' and line.state != 'cancel': #modified
                            write_cancel_ids.append(line.id)
                    else:
                        notcanceled = True
        if write_done_ids:
            self.pool.get('sale.order.line').write(cr, uid, write_done_ids, {'state': 'done'})
        if write_cancel_ids:
            self.pool.get('sale.order.line').write(cr, uid, write_cancel_ids, {'state': 'exception'})
        
        if mode == 'finished':
            return finished
        elif mode == 'canceled':
            return canceled
            if notcanceled:
                return False
            return canceled
sale_order()

class sale_order_line(osv.osv):
    
    _name = 'sale.order.line'
    _inherit = 'sale.order.line'
    
    def force_delete(self, cr, uid, ids, context=None):
        self.pool.get("sale.order.line").write(cr, uid, ids, {'state':'cancel'} ,context)
        return None
    
    def action_modify_after_confirm_add_order_notes(self, cr, uid, ids, new_quantities, old_quantities, context=None):
        order_notes = {}
        for sale_order_line in self.browse(cr, uid, ids, context):
            if order_notes.has_key(sale_order_line.order_id.id):
                previous_order_note = order_notes[sale_order_line.order_id.id]
            elif sale_order_line.order_id.note:
                previous_order_note = sale_order_line.order_id.note
            else:
                previous_order_note = ''
            new_sale_order_note = previous_order_note+"\nLine of product "+sale_order_line.name+" quantity modified from "+str(old_quantities[sale_order_line.id])+" to "+str(new_quantities[sale_order_line.id])
            order_notes[sale_order_line.order_id.id] = new_sale_order_note
            
        for order_note_id in order_notes.keys():
            self.pool.get('sale.order').write(cr, 1, [order_note_id], {'note': order_notes[order_note_id]})
            
        return None
    
    def action_modify_after_confirm_sale_wizard(self, cr, uid, ids, new_quantities, old_quantities, context=None):
        wf_service = netsvc.LocalService("workflow")
        self.action_modify_after_confirm(cr, uid, ids, new_quantities, context)
        
        #find procurements of order line and change their quantities
        cr.execute('''select procurement_order.id, sale_order_line.id 
            from 
            sale_order_line 
            left join stock_move
            left join procurement_order on procurement_order.move_id = stock_move.id
            on stock_move.sale_line_id = sale_order_line.id 
            where sale_order_line.id in %s and procurement_order.id is not null
            ''', (tuple(ids),))
            
        request_result = cr.fetchall()
        new_quantities_for_procurement = dict([(procurement_order_id, new_quantities[sale_order_line_id]) for (procurement_order_id, sale_order_line_id) in request_result])
        self.pool.get('procurement.order').action_modify_after_confirm(cr, 1, new_quantities_for_procurement.keys(), new_quantities_for_procurement, context)
            
        #find stock moves of order line and change quantities
        cr.execute('''select stock_move.id, sale_line_id, stock_move.state, product_qty, picking_id, stock_picking.state, stock_picking.type 
        from stock_move 
        left join stock_picking on stock_move.picking_id = stock_picking.id 
        where sale_line_id in %s''', (tuple(ids),))
        
        request_result = cr.fetchall()
        
        new_quantities_for_stock_move = {}
        stock_moves_to_copy = {}
        pickings_correction_assigned = [] 
        stock_moves_not_done = {}
        stock_moves_done = {}
        stock_moves_out = []
        
        #if a stock move is available, we only need to add to its quantity, the differences between old and new quantity
        for (stock_move_id, sale_order_line_id, move_state, product_qty, picking_id, picking_state, picking_type) in request_result:
            if move_state != 'done':
                stock_moves_not_done[sale_order_line_id, picking_id] = stock_move_id
                new_quantities_for_stock_move[stock_move_id] = product_qty+(new_quantities[sale_order_line_id]-old_quantities[sale_order_line_id])
                if picking_type == 'out':
                    stock_moves_out.append(stock_move_id)
                
        #if a stock move is done, we need to create a new move with the difference, ONLY IF NOT ANY OTHER AVAILABLE MOVE FOR THE SAME ORDER LINE EXIST.
        for (stock_move_id, sale_order_line_id, move_state, product_qty, picking_id, picking_state, picking_type) in request_result:
            if move_state == 'done': 
                if not stock_moves_not_done.has_key((sale_order_line_id, picking_id)) and not stock_moves_done.has_key((sale_order_line_id, picking_id)):
                    if picking_state == 'done':
                        pickings_correction_assigned.append(picking_id) 
                    stock_moves_to_copy[stock_move_id] = new_quantities[sale_order_line_id]-old_quantities[sale_order_line_id]
                stock_moves_done[sale_order_line_id, picking_id] = stock_move_id
                if picking_type == 'out':
                    stock_moves_out.append(stock_move_id)
        
        self.pool.get('stock.move').action_modify_after_confirm(cr, 1, new_quantities_for_stock_move.keys(), new_quantities_for_stock_move, context)
        self.pool.get('stock.move').copy_stock_moves(cr, 1, stock_moves_to_copy.keys(), stock_moves_to_copy, context)
        self.pool.get('stock.move').write(cr, uid, stock_moves_out, {'state':'waiting'}, context)
        
        #change the picking state if necessary
        for pick_assigned in pickings_correction_assigned:
            wf_service.trg_create(uid, 'stock.picking', pick_assigned, cr)
            wf_service.trg_validate(uid, 'stock.picking', pick_assigned, 'correction', cr)
        
        #add a note in sale orders
        self.action_modify_after_confirm_add_order_notes(cr, uid, ids, new_quantities, old_quantities, context)
        
        return None
    
    def action_modify_after_confirm(self, cr, uid, ids, new_quantities, context=None):
        for id in ids:
            #Write new quantity for order line
            self.write(cr, 1, [id], {'product_uom_qty':new_quantities[id]})
        return None
    
sale_order_line()

class purchase_order_line(osv.osv):
    
    _name = 'purchase.order.line'
    _inherit = 'purchase.order.line'
    
    _columns = {
        'order_id_state' : fields.related('order_id', 'state', type="text", string="Order's state")
    }
    
    #GARDE FOU
    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        if isinstance(ids, list) and len(ids)>0:
            cr.execute('select count(*) from purchase_order_line where id in %s', (tuple(ids),))
            request_result = cr.fetchall()
            if request_result[0] != (0,):
                return super(purchase_order_line, self).read(cr, uid, ids, fields=fields, context=context, load=load)
            else:
                return False
        else:
            return super(purchase_order_line, self).read(cr, uid, ids, fields=fields, context=context, load=load)
        
    #GARDE FOU
    def name_get(self, cr, uid, ids, context=None):
        if isinstance(ids, list) and len(ids)>0:
            cr.execute('select count(*) from purchase_order_line where id in %s', (tuple(ids),))
            request_result = cr.fetchall()
            if request_result[0] != (0,):
                return super(purchase_order_line, self).name_get(cr, uid, ids, context)
            else:
                return False
        else:
            return super(purchase_order_line, self).name_get(cr, uid, ids, context)
    
    def action_modify_after_confirm_add_order_notes(self, cr, uid, ids, new_quantities, old_quantities, context=None):
        order_notes = {}
        for purchase_order_line in self.browse(cr, uid, ids, context):
            if order_notes.has_key(purchase_order_line.order_id.id):
                previous_order_note = order_notes[purchase_order_line.order_id.id]
            elif purchase_order_line.order_id.notes:
                previous_order_note = purchase_order_line.order_id.notes
            else:
                previous_order_note = ''
            new_purchase_order_note = previous_order_note+"\nLine of product "+purchase_order_line.name+": quantity modified from "+str(old_quantities[purchase_order_line.id])+" to "+str(new_quantities[purchase_order_line.id])
            order_notes[purchase_order_line.order_id.id] = new_purchase_order_note
        
        for order_note_id in order_notes.keys():
            self.pool.get('purchase.order').write(cr, 1, [order_note_id], {'notes': order_notes[order_note_id]})
            
        return None
    
    def action_modify_after_confirm_purchase_wizard(self, cr, uid, ids, new_quantities, old_quantities, context=None):
        self.action_modify_after_confirm(cr, uid, ids, new_quantities, context)
        
        #find stock moves of purchase order line, and procurement and change their quantities
        stock_move_ids = self.pool.get("stock.move").search(cr, 1, [('purchase_line_id','in',ids)])
        stock_moves = self.pool.get("stock.move").browse(cr, 1, stock_move_ids)
        
        new_quantities_for_stock_move = {}
        new_quantities_for_sale_order_line = {}
        old_quantities_for_sale_order_line = {}
        new_quantities_for_procurement = {}
        
        for stock_move in stock_moves:
            new_quantity = new_quantities[stock_move.purchase_line_id.id]
            old_quantity = old_quantities[stock_move.purchase_line_id.id]
            current_stock_move = stock_move
            chained_stock_moves_id = []
            while current_stock_move:
                chained_stock_moves_id.append(current_stock_move.id)
                new_quantities_for_stock_move[current_stock_move.id] = new_quantity
                if current_stock_move.sale_line_id:
                    new_quantities_for_sale_order_line[current_stock_move.sale_line_id.id] = new_quantity
                    old_quantities_for_sale_order_line[current_stock_move.sale_line_id.id] = old_quantity
                current_stock_move = current_stock_move.move_dest_id
            procurement_ids = self.pool.get('procurement.order').search(cr, 1, ['|',('move_id','in',chained_stock_moves_id),('purchase_id','=',stock_move.purchase_line_id.order_id.id)])
            for procurement_id in procurement_ids:
                new_quantities_for_procurement[procurement_id] = new_quantity
                
        #Add order notes
        self.action_modify_after_confirm_add_order_notes(cr, uid, ids, new_quantities, old_quantities, context)
        self.pool.get('sale.order.line').action_modify_after_confirm_add_order_notes(cr, 1, new_quantities_for_sale_order_line.keys(), new_quantities_for_sale_order_line, old_quantities_for_sale_order_line, context)
        self.pool.get('sale.order.line').action_modify_after_confirm(cr, 1, new_quantities_for_sale_order_line.keys(), new_quantities_for_sale_order_line, context)
        
                    
        self.pool.get('stock.move').action_modify_after_confirm(cr, 1, new_quantities_for_stock_move.keys(), new_quantities_for_stock_move, context)
        
        
        self.pool.get('procurement.order').action_modify_after_confirm(cr, 1, new_quantities_for_procurement.keys(), new_quantities_for_procurement, context)
        return None
    
    def action_modify_after_confirm(self, cr, uid, ids, new_quantities, context=None):
        for id in ids:
            #Write new quantity for order line
            self.write(cr, 1, [id], {'product_qty':new_quantities[id]})
        return None
    
    def force_delete(self, cr, uid, ids, context=None):
        self.pool.get("purchase.order.line").write(cr, uid, ids, {'state':'draft'} ,context)
        self.pool.get("purchase.order.line").unlink(cr, uid, ids, context)
        cr.commit()
        return None
    
purchase_order_line()

class procurement_order(osv.osv):
    
    _name = 'procurement.order'
    _inherit = 'procurement.order'
    
    def action_modify_after_confirm(self, cr, uid, ids, new_quantities, context=None):
        for id in ids:
            self.write(cr, 1, [id], {'product_qty':new_quantities[id], 'product_uos_qty':new_quantities[id]})
        return None
    
    def force_delete(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")
        for procurement_id in ids:
            wf_service.trg_delete(uid, 'procurement.order', procurement_id, cr)

        self.pool.get("procurement.order").write(cr, uid, ids, {'state':'cancel'} ,context)
        
        return None
    
procurement_order()


class stock_move(osv.osv):
    
    _name = 'stock.move'
    _inherit = 'stock.move'
    
    def copy_stock_moves(self, cr, uid, ids, new_stock_moves_quantities, context=None):
        for id in ids:
            self.copy(cr, 1, id, {'product_qty':new_stock_moves_quantities[id], 'product_uos_qty':new_stock_moves_quantities[id], "state":"assigned"}, context)
        return None
    
    def action_modify_after_confirm(self, cr, uid, ids, new_quantities, context=None):
        for id in ids:
            self.write(cr, 1, id, {'product_qty':new_quantities[id], 'product_uos_qty':new_quantities[id]}, context)
        return None
    
    def force_delete(self, cr, uid, ids, context=None):
        self.pool.get("stock.move").write(cr, uid, ids, {'state':'draft'} ,context)
        self.pool.get("stock.move").unlink(cr, uid, ids, context)
        return None
                        
stock_move()

