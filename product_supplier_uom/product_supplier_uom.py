from openerp import models, fields, api


class ProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'

    @api.model
    def _get_supplier_uom(self):
        product_tmpl_id = self.env['product.template'].browse(self.env.context.get('product_tmpl_id',False))
        if product_tmpl_id and product_tmpl_id.uom_po_id:
            return product_tmpl_id.uom_po_id
    
    product_uom = fields.Many2one(comodel_name='product.uom',default=_get_supplier_uom,required=True,readonly=False,help="This comes from the product form by default. But you can provide a specific uom for one supplier")
    