from openerp import models, fields, pooler
import threading

class elneo_supplier_price_update_wizard(models.TransientModel):
    _name="elneo.supplier.price.update.wizard"
    
    increase_percent = fields.Float('Increase Percent',required=True)
    supplier_id = fields.Many2one('res.partner','Supplier',domain=[('supplier','=',True)],required=True)
    
    
    def affect_prices(self,cr,uid,ids,context=None):
        res = {}
        
        for wizard in self.pool.get("elneo.supplier.price.update.wizard").browse(cr,uid,ids,context=context):
            if wizard.supplier_id.id :
                sql = """     
                INSERT INTO pricelist_partnerinfo (price,min_quantity,name,brut_price,discount,public_price,suppinfo_id,date,update_methode,write_uid)
                    SELECT (price * """ + str(1.00+(wizard.increase_percent / 100)) + """) AS price,min_quantity,name,brut_price,discount,public_price,suppinfo_id,CURRENT_TIMESTAMP,'manual',""" + str(uid) + """ FROM pricelist_partnerinfo WHERE id IN 
                        (SELECT id FROM 
                            (SELECT max(pp.id) AS id,max(pp.date) AS date, pp.min_quantity, ps.id AS ps_id FROM pricelist_partnerinfo pp JOIN product_supplierinfo ps ON pp.suppinfo_id = ps.id WHERE ps.name = """ + str(wizard.supplier_id.id) + """ GROUP BY pp.min_quantity, ps.id) AS req1)
        
                """
                cr.execute(sql)
        
        thread_compute = threading.Thread(target=self.update_sale_prices,args=(cr, uid, ids, context))
        thread_compute.start()
        #self.update_sale_prices(cr, uid, ids, context)
                
        return res
    
    def update_sale_prices(self,cr,uid,ids,context=None):
        res = True
        
        cr = pooler.get_db(self._cr.dbname).cursor()
        uid, context = self.env.uid, self.env.context
        
        try:
            for wizard in self.pool.get("elneo.supplier.price.update.wizard").browse(cr,uid,ids,context=context):
                if wizard.supplier_id.id :
                    suppinfo_ids = self.pool.get('product.supplierinfo').search(cr,uid,[('name','=',wizard.supplier_id.id)],context=context)
                    for suppinfo in self.pool.get('product.supplierinfo').browse(cr,uid,suppinfo_ids,context=context):
                        product_ids = self.pool.get('product.product').search(cr,uid,[('product_tmpl_id','=',suppinfo.product_id.id)],context=context)
                        for product in self.pool.get('product.product').browse(cr,uid,product_ids,context=context):
                            self.pool.get('product.product').write(cr,uid,product.id,{},context=context)

        except Exception,e:
            raise Warning('Percent Sale Price Update Failed','Error during sale price update' + unicode(e))
        finally:
            try:                
                cr.commit()
            except Exception:
                pass
            try:                
                cr.close()
            except Exception:
                pass
        return res
    
    
elneo_supplier_price_update_wizard()