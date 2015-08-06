
from openerp import models, fields, api


class serial_number_wizard(models.TransientModel):
    _name = "serial.number.wizard"
    #in shop sale, if a product need a serial number, this wizard is launched
    
    @api.model
    def default_get(self,fields):
        res = super(serial_number_wizard, self).default_get(fields=fields)
        
        sale_order_ids = self.env.context.get('active_ids', [])
        
        lines = []
        
        for sale_order_line in self.pool.get("sale.order").browse(sale_order_ids[0]).order_line:
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
                    raise Warning(_('Please enter %s serial number of product %s')%(str(serial_number_line.sale_line_id.product_uom_qty),serial_number_line.product_name))
                else:
                    new_maintenance_elements = maintenance_element_pool.create_default(serial_number_line.serial_number, serial_number_line.sale_line_id.id)
            
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
    