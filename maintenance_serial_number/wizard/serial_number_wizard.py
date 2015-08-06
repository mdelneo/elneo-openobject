from tools.translate import _
from osv import osv, fields
import time
import netsvc

class serial_number_wizard(osv.osv_memory):
    _name = "serial.number.wizard"
    #in shop sale, if a product need a serial number, this wizard is launched
    
    def default_get(self, cr, uid, fields, context=None):
        res = super(serial_number_wizard, self).default_get(cr, uid, fields, context=context)
        
        sale_order_ids = context.get('active_ids', [])
        
        lines = []
        
        for sale_order_line in self.pool.get("sale.order").browse(cr, uid, sale_order_ids[0], context).order_line:
            if sale_order_line.product_id.serialnumber_required:
                lines.append({"product_name":sale_order_line.product_id.default_code, "sale_line_id":sale_order_line.id})
        
        
        res["serial_number_lines"]=lines
        
        return res
    
    def validate_serialnumbers(self,cr,uid,ids,context=None):
        maintenance_element_pool = self.pool.get("maintenance.element")
        wiz = self.browse(cr, uid, ids[0], context)
        
        for serial_number_line in wiz.serial_number_lines:
            if not serial_number_line.serial_number or serial_number_line.serial_number.count(';') != serial_number_line.sale_line_id.product_uom_qty - 1:
                raise osv.except_osv(_('Processing Error'),\
                                _('Please enter %s serial number of product %s')%(str(serial_number_line.sale_line_id.product_uom_qty),serial_number_line.product_name))
            else:
                new_maintenance_elements = maintenance_element_pool.create_default(cr, uid, serial_number_line.serial_number, serial_number_line.sale_line_id.id, context=context)
        
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'sale.order', context.get('active_ids')[0], 'order_confirm', cr)
            
        return {'type': 'ir.actions.act_window_close'}
        
    
    _columns = {
        "serial_number_lines":fields.one2many("serial.number.line.wizard", "wizard_id", string="Serial number lines"), 
    }
serial_number_wizard()

class serial_number_line_wizard(osv.osv_memory):
    _name = "serial.number.line.wizard"
    _columns = {
        'wizard_id':fields.many2one("serial.number.wizard", string="Wizard"),
        "sale_line_id":fields.many2one("sale.order.line", "sale line"),
        "product_name":fields.char('Product name', size=255),
        "serial_number":fields.char('Serial number', size=255), 
    }
serial_number_line_wizard()