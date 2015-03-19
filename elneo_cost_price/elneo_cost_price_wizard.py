from openerp import models,fields,api, pooler, netsvc
from openerp.tools.float_utils import float_compare, float_round
import threading
import openerp
import smtplib

class res_partner_cost_price(models.TransientModel):
    _name = "res.partner.cost.price"
    
    @api.multi
    def compute_costprices(self):
        thread_compute_costprices = threading.Thread(target=self._compute_costprices, args=())
        thread_compute_costprices.start()
        return {'type': 'ir.actions.act_window_close'}
    
    
    def _compute_costprices(self):
        cr2 = pooler.get_db(self._cr.dbname).cursor()
        uid, context = self.env.uid, self.env.context
        with api.Environment.manage():
            self.env = api.Environment(cr2, uid, context)

            try:
                supplierinfos = self.env["product.supplierinfo"].search([('name','in',self._context.get('active_ids', []))])
                product_tmpls = [supplier_info.product_tmpl_id for supplier_info in supplierinfos]
                
                if product_tmpls:
                    original_products = product_tmpls
                    
                    k = 100
                    i = 0
                    l = len(original_products)
                    product_tmpls = original_products[0:l%k]
                    
                    while i <= l/k:
                        for product_tmpl in product_tmpls:
                            product_tmpl._get_cost_price()
                        self.env.cr.commit()
                        product_tmpls = original_products[(i)*k+l%k:(i+1)*k+l%k]
                        i = i+1
            finally:
                try:                
                    self.env.cr.commit()
                except Exception:
                    pass
                try:                
                    self.env.cr.close()
                except Exception:
                    pass
            
        return {'type': 'ir.actions.act_window_close'}
        
res_partner_cost_price()