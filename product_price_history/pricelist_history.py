from openerp import models, fields, api
from openerp.exceptions import Warning
import openerp.addons.decimal_precision as dp
from datetime import datetime


class pricelist_history(models.Model):
    _name = 'pricelist.partnerinfo.history'
    
    min_quantity=fields.Float('Quantity', required=True, help="The minimal quantity to trigger this rule, expressed in the supplier Unit of Measure if any or in the default Unit of Measure of the product otherrwise.")
    
    suppinfo_id = fields.Many2one('product.supplierinfo', 'Partner Information', required=True, ondelete='cascade')
    
    brut_price=fields.Float('Brut Price',  help='This price is considered as the brut price => unite price = ((100-discount)/100 * brut price)',)
    
    date = fields.Datetime('Date')
    
    update_method = fields.Selection((('manual','Manual'),('price_list_file','Price List File'),('purchase_order_confirmation','Purchase Order Confirmation')),   'Update Method', size=30, store=True)
    
    discount = fields.Float('Discount (%)', digits=(16, 2))
    
    price = fields.Float('Unit Price', required=True, digits_compute=dp.get_precision('Product Price'), help="This price will be considered as a price for the supplier UoM if any or the default Unit of Measure of the product otherwise")
    
    #public_price = fields.Float('Unit Price', required=True, digits_compute=dp.get_precision('Product Price'), help="This price will be considered as a price for the supplier UoM if any or the default Unit of Measure of the product otherwise")
    
    
    
    _order = "date DESC"
    
pricelist_history()

    
class pricelist_partnerinfo(models.Model):
    _inherit = 'pricelist.partnerinfo'
        
    _sql_constraints = [('quantity_uniq', 'unique(min_quantity, suppinfo_id)',
            'The pricelist for the product can contain unique quantities'),]
    

    @api.one
    def write(self,vals):
        value = {}
        
        if (vals.has_key('suppinfo_id')):
            value.update({'suppinfo_id':vals['suppinfo_id']})
        else:
            if self.suppinfo_id:
                value.update({'suppinfo_id':self.suppinfo_id.id})
            else:
                raise Warning(_('Error'),('The supplier information is missing to modify this pricelist line. Contact Support!'))
        
        
        if (vals.has_key('min_quantity')):
            value.update({'min_quantity':vals['min_quantity']})
        else:
            value.update({'min_quantity':self.min_quantity})
            
        if (vals.has_key('discount')):
            value.update({'discount':vals['discount']})
        else:
            value.update({'discount':self.discount})
            
        if (vals.has_key('price')):
            value.update({'price':vals['price']})
        else:
            value.update({'price':self.price})
            
        if (vals.has_key('brut_price')):
            value.update({'brut_price':vals['brut_price']})
        else:
            value.update({'brut_price':self.brut_price})
            
        value.update({'date':datetime.now()})
        
        value.update({'update_method':'manual'})
        
        '''    
        if (vals.has_key('public_price')):
            value.update({'public_price':vals['public_price']})
        else:
            value.update({'public_price':self.public_price})
            
        '''    
        self.env['pricelist.partnerinfo.history'].create(value)
        
        
        return super(pricelist_partnerinfo,self).write(vals)
    
    @api.model
    def create(self,vals):
        value = {}
        
        if (vals.has_key('suppinfo_id')):
            value.update({'suppinfo_id':vals['suppinfo_id']})
        else:
            raise Warning(_('Error'),('The supplier information is missing to insert this pricelist line. Contact Support!'))
        
        
        if (vals.has_key('min_quantity')):
            value.update({'min_quantity':vals['min_quantity']})
        else:
            value.update({'min_quantity':1.0})
            
        if (vals.has_key('discount')):
            value.update({'discount':vals['discount']})
        else:
            value.update({'discount':0.0})
            
        if (vals.has_key('price')):
            value.update({'price':vals['price']})
        else:
            value.update({'price':0.0})
            
        if (vals.has_key('brut_price')):
            value.update({'brut_price':vals['brut_price']})
        else:
            value.update({'brut_price':0.0})
            
        value.update({'date':datetime.now()})
        value.update({'update_method':'manual'})
            
        '''
        if (vals.has_key('public_price')):
            value.update({'public_price':vals['public_price']})
        else:
            value.update({'public_price':0.0})
  
        '''    
        self.env['pricelist.partnerinfo.history'].create(value)
        
        
        return super(pricelist_partnerinfo,self).create(vals)
    
pricelist_partnerinfo()


class product_supplierinfo(models.Model):
    _inherit = 'product.supplierinfo'
    
    pricelist_history_ids = fields.One2many('pricelist.partnerinfo.history','suppinfo_id',string='Pricelist History',readonly=True)
    net_unit_price = fields.Float(string='Net unit price', compute='get_price_for_one')
    
    @api.one
    def get_price_for_one(self):
        for pricelist in self.pricelist_ids:
            if pricelist.min_quantity == 1:
                self.net_unit_price = pricelist.price
                return
    
product_supplierinfo()