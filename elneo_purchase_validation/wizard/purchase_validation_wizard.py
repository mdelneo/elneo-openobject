from openerp import models, fields, _, api

class PurchaseValidationWizard(models.TransientModel):
    _inherit = 'purchase.validation.wizard'
              
    @api.model
    def _get_pricelist_values_to_update(self, purchase_validation_line,pricelist):
        res = super(PurchaseValidationWizard,self)._get_pricelist_values_to_update(purchase_validation_line, pricelist)
        
        if not purchase_validation_line.new_brut_price:
            brut_price = purchase_validation_line.new_price / (1-pricelist.discount/100)
        else:
            brut_price = purchase_validation_line.new_brut_price
            
        if not purchase_validation_line.new_discount:
            discount = pricelist.discount
        else:
            discount = purchase_validation_line.new_discount
         
        res.update({'brut_price':brut_price,
                    'discount':discount
                    })
         
        return res
    
    @api.model
    def _update_sale_line(self,purchase_validation_line):
        
        res = super(PurchaseValidationWizard,self)._update_sale_line(purchase_validation_line)
        
        sale_order_to_update = set()
        sale_lines = self._get_sale_order_lines(purchase_validation_line)
        
        #compute cost price of sale order
        for sale_line in sale_lines:
            sale_order_to_update.add(sale_line.order_id.id)
            
            change = sale_line.product_id_change(sale_line.order_id.pricelist_id.id, sale_line.product_id.id, qty=sale_line.product_uom_qty,
                uom=sale_line.product_uom.id, qty_uos=sale_line.product_uos_qty, uos=sale_line.product_uos.id, name=sale_line.name, partner_id=sale_line.order_id.partner_id.id,
                lang=sale_line.order_id.partner_id.lang, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False)
            
            #product_cost_price = product_pool._get_cost_price(cr, uid, [sale_line.product_id.id], args={'compute_cost_price':sale_line.product_id.compute_cost_price, 'cost_price_fixed':sale_line.product_id.cost_price_fixed})[sale_line.product_id.id]
            product_cost_price = change['value']['purchase_price'] 
            new_cost_price = self.env['sale.order.line'].compute_cost_price(sale_line.product_id, sale_line.order_id.partner_id, product_cost_price)
            sale_line.purchase_price = new_cost_price
            
            for invoice_line in sale_line.invoice_lines:
                invoice_line.cost_price = new_cost_price
                
        return res
    
    @api.multi         
    def update_purchase(self):
        res= super(PurchaseValidationWizard,self).update_purchase()
        
        return res
        
class PurchaseValidationLineWizard(models.TransientModel):
    _inherit = 'purchase.validation.line.wizard'
        
    new_brut_price = fields.Float("New brut price", digits=(20, 6))
    new_discount = fields.Float('New Discount')
    
            