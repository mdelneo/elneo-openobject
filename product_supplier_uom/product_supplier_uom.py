from openerp import models, fields, api


class ProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'

    @api.model
    def _get_supplier_uom(self):
        product = self.env['product.product'].browse(self.env.context.get('product_id',False))
        if product and product.uom_po_id:
            return product.uom_po_id
    
    product_uom = fields.Many2one(comodel_name='product.uom',default=_get_supplier_uom,required=True,readonly=False,help="This comes from the product form by default. But you can provide a specific uom for one supplier")
    