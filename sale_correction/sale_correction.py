from openerp import models, fields, api, _, SUPERUSER_ID
from openerp.exceptions import Warning

class stock_move(models.Model):
    _inherit = 'stock.move'
    
    @api.multi
    def force_delete(self):
        for m in self:
            m.state = 'draft'
            m.unlink()
    

class procurement_order(models.Model):
    _inherit = 'procurement.order'
    
    @api.multi
    def force_delete(self):
        for p in self:
            p.state = 'cancel'
            p.unlink()
        

class purchase_order_line(models.Model):
    _inherit = 'purchase.order.line'
    
    
    @api.multi
    def force_delete(self):
        for l in self:
            l.state = 'cancel'
            l.unlink()
            
    def get_procurements(self):
        return self.env['procurement.order'].search([('purchase_line_id','=',self.id)])
    
    def get_moves(self):
        #find stock moves of order line and change quantities
        out_stock_moves = self.env['stock.move'].search([('procurement_id.purchase_line_id','=',self.id)])
        stock_moves = []
        for out_stock_move in out_stock_moves:
            current_stock_move = out_stock_move
            while current_stock_move:
                stock_moves.extend(current_stock_move)
                current_stock_move = self.env['stock.move'].search([('move_dest_id','=',current_stock_move.id)])
                if current_stock_move and current_stock_move[0].state == 'done':
                    raise Warning(_("You can't modify line related to 'done' moves."))
        return self.env['stock.move'].browse([m.id for m in stock_moves])


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    @api.multi
    def force_delete(self):
        for s in self:
            s.state = 'cancel'
            s.unlink()
            
    def get_purchase_order_line(self):
        procurements = self.env['procurement.order'].search([('sale_line_id','=',self.id),('purchase_id','!=',False)])
        for procurement in procurements:
            if procurement and procurement.purchase_line_id:
                return procurement.purchase_line_id
        return self.env['purchase.order.line']
        
            
    
    def get_procurements(self):
        return self.env['procurement.order'].search([('sale_line_id','=',self.id)])
    
    def get_moves(self):
        #find stock moves of order line and change quantities
        out_stock_moves = self.env['stock.move'].search([('procurement_id.sale_line_id','=',self.id)])
        stock_moves = []
        for out_stock_move in out_stock_moves:
            current_stock_move = out_stock_move
            while current_stock_move:
                stock_moves.extend(current_stock_move)
                current_stock_move = self.env['stock.move'].search([('move_dest_id','=',current_stock_move.id)])
                if current_stock_move and current_stock_move[0].state == 'done':
                    raise Warning(_("You can't modify line related to 'done' moves."))
        return self.env['stock.move'].browse([m.id for m in stock_moves])