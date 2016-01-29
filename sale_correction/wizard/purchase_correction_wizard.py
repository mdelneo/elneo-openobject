from openerp import models, fields, api
from openerp.exceptions import Warning


class purchase_delete_line_wizard(models.TransientModel):
    _name = 'purchase.delete.line.wizard'
    
    
    def _get_purchase_order_line_id(self):
        return self.env.context.get('active_id')
    
    purchase_order_line_id=fields.Many2one('purchase.order.line', 'Purchase Order',default=_get_purchase_order_line_id)
    
    
    def delete_line(self, cr, uid, ids, context=None):
        purchase_order_line_ids = []
        
        for wiz in self.browse(cr, uid, ids, context):
            if wiz.purchase_order_line_id.order_id.state != 'approved':
                raise osv.except_osv(_('Error'), _('You can only apply that modification on "approved" order lines.'))
            purchase_order_line_ids.append(wiz.purchase_order_line_id.id)
        
        
        #find stock moves, procurement and sale_order_lines of purchase order line 
        stock_move_ids = self.pool.get("stock.move").search(cr, uid, [('purchase_line_id','in',purchase_order_line_ids)])
        stock_moves = self.pool.get("stock.move").browse(cr, uid, stock_move_ids)
        
        stock_moves_to_delete = []
        sale_order_lines_to_delete = []
        procurements_to_delete = []
        
        for stock_move in stock_moves:
            current_stock_move = stock_move
            chained_stock_moves_id = []
            while current_stock_move:
                chained_stock_moves_id.append(current_stock_move.id)
                stock_moves_to_delete.append(current_stock_move.id)
                if current_stock_move.sale_line_id:
                    sale_order_lines_to_delete.append(current_stock_move.sale_line_id.id)
                    if current_stock_move.sale_line_id.procurement_id:
                        procurements_to_delete.append(current_stock_move.sale_line_id.procurement_id.id) 
                current_stock_move = current_stock_move.move_dest_id
            procurements_to_delete.extend(self.pool.get('procurement.order').search(cr, uid, [('move_id','in',chained_stock_moves_id)]))
        
        #delete stock moves, procurement and sale_order_lines of purchase order line
        self.pool.get("sale.order.line").force_delete(cr, uid, sale_order_lines_to_delete, context)
        self.pool.get("procurement.order").force_delete(cr, uid, procurements_to_delete, context)
        self.pool.get("purchase.order.line").force_delete(cr, uid, purchase_order_line_ids, context)        
        self.pool.get("stock.move").force_delete(cr, uid, stock_moves_to_delete, context)
        
        return {'type': 'ir.actions.act_window_close'}
    
purchase_delete_line_wizard()


class PurchaseChangeQuantityWizard(models.TransientModel):
    _name = 'purchase.change.quantity.wizard'
    
    @api.model
    def _get_old_quantity(self):
        return self.env['purchase.order.line'].read(self.env.context.get('active_id'))['product_qty']
    
    @api.model
    def _get_purchase_order_line_id(self):
        return self.env.context.get('active_id')
    

    new_quantity = fields.Float("New quantity",default=_get_old_quantity)
    old_quantity = fields.Float("Old quantity",default=_get_old_quantity())
    purchase_order_line_id = fields.Many2one('purchase.order.line', 'Purchase order line',default=_get_purchase_order_line_id)
    
    @api.multi
    def change_quantity(self):
        purchase_order_lines = self.env['purchase.order.line']
        new_quantities = {}
        old_quantities = {}
        
        for wizard in self:
            if wizard.purchase_order_line_id.order_id.state != 'approved':
                raise Warning(_('You can only apply that modification on "approved" order lines.'))
            else:
                purchase_order_lines+=wizard.purchase_order_line_id.id
                new_quantities[wizard.purchase_order_line_id.id] = wizard.new_quantity
                old_quantities[wizard.purchase_order_line_id.id] = wizard.old_quantity 
                
        self.action_modify_after_confirm_purchase_wizard(purchase_order_lines, new_quantities, old_quantities)
        
        return {'type': 'ir.actions.act_window_close'}
    
    @api.model
    def action_modify_after_confirm_add_order_notes(self, purchase_lines, new_quantities, old_quantities):

        for purchase_order_line in purchase_lines:
            purchase_order_line.order_id.message_post(body=_('Line of product %s : quantity modified from %s to %s') % (purchase_order_line.name,str(old_quantities[purchase_order_line.id]),str(new_quantities[purchase_order_line.id])))
            
        return True
    
    @api.model
    def action_modify_after_confirm_purchase_wizard(self,purchase_lines,new_quantities, old_quantities):
        self.action_modify_after_confirm(purchase_lines, new_quantities)
        
        #find stock moves of purchase order line, and procurement and change their quantities
        stock_moves = self.env['stock.move'].sudo().search([('purchase_line_id','in',purchase_lines._ids)])
        
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
            procurements = self.env['procurement.order'].sudo().search(['|',('move_id','in',chained_stock_moves_id),('purchase_id','=',stock_move.purchase_line_id.order_id.id)])
            for procurement in procurements:
                new_quantities_for_procurement[procurement.id] = new_quantity
                
        #Add order notes
        
        self.action_modify_after_confirm_add_order_notes(new_quantities, old_quantities)
        if not self.env.context.get('correct_from_sale',False):
            self.env['sale.correction.change.sale'].sudo().with_context(correct_from_purchase=True).action_modify_after_confirm_add_notification(new_quantities_for_sale_order_line.keys(), new_quantities_for_sale_order_line, old_quantities_for_sale_order_line)
            self.env['sale.correction.change.sale'].sudo().with_context(correct_from_purchase=True).action_modify_after_confirm(new_quantities_for_sale_order_line.keys(), new_quantities_for_sale_order_line)
        
                    
        self.env['stock.move'].sudo().action_modify_after_confirm(new_quantities_for_stock_move.keys(), new_quantities_for_stock_move)
        
        
        self.env['procurement.order'].action_modify_after_confirm(new_quantities_for_procurement.keys(), new_quantities_for_procurement)
        return True
    
    @api.model
    def action_modify_after_confirm(self,purchase_lines, new_quantities):
        for line in purchase_lines:
            #Write new quantity for order line
            line.write({'product_qty':new_quantities[line.id]})
        return None
    
    @api.model
    def force_delete(self, purchase_lines):
        purchase_lines.write({'state':'draft'})
        purchase_lines.unlink()
       
        #cr.commit()
        return True
    