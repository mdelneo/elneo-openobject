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
    def _prepare_supplier_fee_line(self,picking_id, invoice_id):
        fee_product_id = self.env['ir.config_parameter'].get_param('supplier_fee.purchase_invoice_fee_product',False)
        if not fee_product_id:
            return None
        fee_product_id = int(fee_product_id)
        fee_product = self.env['product.product'].browse(fee_product_id)
        invoice = self.env['account.invoice'].browse(invoice_id)
        if invoice.type != 'in_invoice':
            return None
        product_id_change_res = self.env['account.invoice.line'].product_id_change(fee_product_id, fee_product.uom_po_id.id, partner_id=invoice.partner_id.id)
        invoice_line_vals = product_id_change_res['value']
        
        
        picking = self.env['stock.picking'].browse(picking_id)
        account_id = fee_product.property_account_expense.id
        if not account_id:
            account_id = fee_product.categ_id.property_account_expense_categ.id
        
        taxes = fee_product.taxes_id
        partner = picking.partner_id or False
        fp = invoice.fiscal_position or partner.property_account_position
        
        if partner:
            account_id = fp.map_account(account_id)
            taxes_ids = fp.map_tax(taxes)
            taxes_ids = taxes_ids.mapped('id')
        else:
            taxes_ids = [x.id for x in taxes]
            
            
        invoice_line_vals.update({
               'product_id':fee_product_id,
               'invoice_id':invoice_id,
               'invoice_line_tax_id': [(6, 0, taxes_ids)],
               'account_id': account_id,
               })
        
        return invoice_line_vals
        

    @api.model
    def _invoice_create_line(self, moves, journal_id, inv_type='out_invoice'):
        res = super(stock_picking, self)._invoice_create_line(moves, journal_id, inv_type)
        
        for invoice_id in res:
            if moves and moves[0]:
                invoice_line_vals = self._prepare_supplier_fee_line(moves[0].picking_id.id, invoice_id)
                if invoice_line_vals:
                    self.env['account.invoice.line'].create(invoice_line_vals)
        return res
        