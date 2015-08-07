'''
Created on 28 mai 2013

@author: technofluid
'''
from osv import osv, fields
import netsvc

class wizard_sale_confirm(osv.osv_memory):
    _name = 'wizard.sale.confirm'
    
    
    def _get_default_installation(self, cr, uid, context=None):
        if 'partner_id' in context:
            installation_ids = self.pool.get("maintenance.installation").search(cr, uid, [('partner_id','=',context['partner_id'])], context=context)
            if len(installation_ids) == 1:
                return installation_ids[0]
        return None
    
    _columns = {
        'installation_id':fields.many2one('maintenance.installation', 'Installation')
    } 
    
    _defaults = {
        'installation_id':_get_default_installation
    }
    
    def validate(self, cr, uid, ids, context):
        for wizard in self.browse(cr, uid, ids, context):
            sale = self.pool.get("sale.order").browse(cr, uid, context.get("sale_id"), context)
            self.pool.get("sale.order").write(cr, uid, [sale.id], {'installation_id':wizard.installation_id.id}, context=context)
            for line in sale.order_line:
                if line.product_id.maintenance_product:
                    #find maintenance element model associated with product of line
                    cr.execute('select model_id from maintenance_element_model_product_rel where product_id = %s', (line.product_id.id,))
                    model_id = cr.fetchone()
                    if model_id:
                        model_id = model_id[0]
                    
                    for i in range(0,int(line.product_uom_qty)):
                        maintenance_element = {
                            'installation_id':wizard.installation_id.id,
                            'name':line.product_id.default_code,
                            'product_id':line.product_id.id, 
                            'sale_order_line_id':line.id, 
                            'element_model_id':model_id,                             
                        }
                        
                        if line.product_id.maintenance_element_type_id:
                            maintenance_element['element_type_id'] = line.product_id.maintenance_element_type_id.id
                            
                        if line.product_id.default_supplier_id:
                            maintenance_element['supplier_id'] = line.product_id.default_supplier_id.id 
                             
                        self.pool.get('maintenance.element').create(cr,uid,maintenance_element,context)
        
        wf_service = netsvc.LocalService("workflow")
        wf_service.trg_validate(uid, 'sale.order', context.get("sale_id"), 'order_confirm', cr)
        return {'type': 'ir.actions.act_window_close'}    
        
wizard_sale_confirm()