
from openerp import models, fields, api, _
from openerp.exceptions import Warning
from distlib._backport.shutil import move


class sale_order(models.Model):
    _inherit='sale.order'
    
    
    @api.one
    def shop_sale_ship(self):
        for line in self.order_line:
            for element in line.maintenance_element_ids:
                for move in self.picking_ids.filtered(lambda r:r.picking_type_id.code=='outgoing').move_lines:
                    if move.product_id == element.product_id:
                        if element.product_id.unique_serial_number:
                            moves = self._split_move(move)
                            
                            if len(moves) != len(element.serial_number.split(';')):
                                raise Warning(_('The quantity to deliver is not the same as serial numbers for the product : %s' % line.product_id.default_code))
                            for new_move in moves:
                                self._assign_serial(new_move, element.serial_number, element.product_id)
                        else:
                            self._assign_serial(move, element.serial_number, element.product_id)
                            
        super(sale_order,self).shop_sale_ship()
    
    @api.model
    def _assign_serial(self,move,serial,product):
        if not move or not serial:
            return False
        
        lot_id = self.env['stock.production.lot'].create({'name':serial,
                                                     'product_id':product.id
                                                     })
            
        move.restrict_lot_id = lot_id
            
            
    
    @api.model
    @api.returns('stock.move')
    def _split_move(self,move):
        res_moves = self.env['stock.move']
        if move.product_uom_qty > 1:
            new_move = self.env['stock.move'].split(move=move,qty=1)
            res_moves += self.env['stock.move'].browse(new_move)
            self._split_move(move)
        else:
            return move
        
        return res_moves
                        


class serial_number_wizard(models.TransientModel):
    _name = "serial.number.wizard"
    #in shop sale, if a product need a serial number, this wizard is launched
    
    @api.model
    def default_get(self,fields):
        res = super(serial_number_wizard, self).default_get(fields)
        
        sale_order_ids = self.env.context.get('active_ids', [])
        
        lines = []
        
        for sale_order_line in self.env['sale.order'].browse(sale_order_ids[0]).order_line:
            if sale_order_line.product_id.serialnumber_required:
                lines.append({"product_name":sale_order_line.product_id.default_code, "sale_line_id":sale_order_line.id})
        
        
        res["serial_number_lines"]=lines
        
        return res
    
    @api.multi
    def validate_serialnumbers(self):
        maintenance_element_pool = self.env['maintenance.element']
        
        for wizard in self:
            for serial_number_line in wizard.serial_number_lines:
                if not serial_number_line.serial_number or serial_number_line.serial_number.count(';') != serial_number_line.sale_line_id.product_uom_qty - 1:
                    raise Warning(_('Please enter %s serial number for product %s')%(str(serial_number_line.sale_line_id.product_uom_qty),serial_number_line.product_name))
                else:
                    new_maintenance_elements = maintenance_element_pool.create_default(serial_number_line.serial_number, serial_number_line.sale_line_id.id)
            
            #self._assign_serial_moves()
            
            
            sale_order = self.env['sale.order'].browse(self.env.context.get('active_ids')[0])
            sale_order.signal_workflow('order_confirm')
            
        return {'type': 'ir.actions.act_window_close'}
        
    serial_number_lines=fields.One2many("serial.number.line.wizard", "wizard_id", string="Serial number lines")
    
    
    

class serial_number_line_wizard(models.TransientModel):
    _name = "serial.number.line.wizard"
    
    wizard_id = fields.Many2one("serial.number.wizard", string="Wizard")
    sale_line_id=fields.Many2one("sale.order.line", "sale line")
    product_name = fields.Char('Product name', size=255)
    serial_number = fields.Char('Serial number', size=255)
    