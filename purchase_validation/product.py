
from openerp import models, fields, api, _
from datetime import datetime
from openerp.exceptions import Warning

class product_product(models.Model):
    _inherit = "product.product"
    
    '''
    @return: old prices indexed by product_id for the supplier and minimum quantities passed by parameter
    ''' 
    @api.multi
    def update_price_for_supplier(self, supplier_id, price,update_price = False, brut_price = False, price_quantity = 1):
       
        supplier_found = False
        result={}
        for product in self:
            for supplierinfo in product.product_tmpl_id.seller_ids:
                if supplierinfo.name.id == supplier_id:
                    supplier_found = True
                    pricelist_partnerinfo_found = False
                    for pricelist in supplierinfo.pricelist_ids:
                        if pricelist.min_quantity == price_quantity:
                            pricelist_partnerinfo_found = True
                            if not brut_price:
                                brut_price = price
                                #brut_price = price / (1-partner_info.discount/100)
                            #if not discount:
                                #discount = partner_info.discount
                            result[product.id] = (pricelist.price, pricelist.min_quantity)
                            
                            #get last public price
                            self.env.cr.execute('select public_price from pricelist_partnerinfo where suppinfo_id = %s and public_price is not null order by id desc limit 1',(supplierinfo.id,))
                            last_public_price_tuple = self.env.cr.fetchone()
                            if last_public_price_tuple:
                                last_public_price = last_public_price_tuple[0]
                            else:
                                last_public_price = 0
                            
                            
                            pricelist.write({'public_price':last_public_price,'min_quantity':price_quantity,'date':datetime.today(),'price':price, 'suppinfo_id':supplierinfo.id, 'brut_price':brut_price, })
                            break
                    if not pricelist_partnerinfo_found:
                        result[product.id] = False
                        self.env['pricelist.partnerinfo'].create({'min_quantity':price_quantity, 'date':datetime.today(),'price':price, 'suppinfo_id':supplierinfo.id, 'brut_price':brut_price,})
                continue
            if not supplier_found:
                supplier = self.env['res.partner'].browse(supplier_id)
                raise Warning(_('Operation canceled'),_("Product '%s' has not supplier '%s' configured. Please complete it before.") % (product.default_code, supplier.name))
            product.write({}) #update stored cost_price function field
        return result
    
product_product()
        