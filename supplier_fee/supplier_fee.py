from openerp import models,fields,api, _, workflow
from datetime import datetime, timedelta
from openerp.exceptions import ValidationError
from openerp.osv import osv


class purchase_config_settings(models.TransientModel):
    _inherit = 'purchase.config.settings'

    purchase_invoice_fee_product = fields.Many2one('product.product', string="Product for fees")

    @api.multi
    def set_purchase_invoice_fee_product(self):
        if self.purchase_invoice_fee_product:
            self.env['ir.config_parameter'].set_param('supplier_fee.purchase_invoice_fee_product',self.purchase_invoice_fee_product.id)
        else:
            self.env['ir.config_parameter'].set_param('supplier_fee.purchase_invoice_fee_product',None)

    @api.model
    def get_default_purchase_invoice_fee_product(self,fields):
        purchase_invoice_fee_product = self.env['ir.config_parameter'].get_param('supplier_fee.purchase_invoice_fee_product',False)
        return {'purchase_invoice_fee_product':int(purchase_invoice_fee_product)}

class stock_picking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _invoice_create_line(self, moves, journal_id, inv_type='out_invoice'):
        res = super(stock_picking, self)._invoice_create_line(moves, journal_id, inv_type)
        fee_product_id = self.env['ir.config_parameter'].get_param('supplier_fee.purchase_invoice_fee_product',False)
        if not fee_product_id:
            return res
        fee_product_id = int(fee_product_id)
        fee_product = self.env['product.product'].browse(fee_product_id)
        for invoice_id in res:
            invoice = self.env['account.invoice'].browse(invoice_id)
            if invoice.type != 'in_invoice':
                continue
            product_id_change_res = self.env['account.invoice.line'].product_id_change(fee_product_id, fee_product.uom_po_id.id, partner_id=invoice.partner_id.id)
            invoice_line_vals = product_id_change_res['value']
            invoice_line_vals['product_id'] = fee_product_id
            invoice_line_vals['invoice_id'] = invoice_id
            self.env['account.invoice.line'].create(invoice_line_vals)
        return res
        