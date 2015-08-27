from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
from openerp import models,fields,api,_
from operator import itemgetter
import re
from openerp.exceptions import ValidationError 

class account_invoice_validation_problem(models.Model):
    _name = 'account.invoice.validation.problem'
    name = fields.Char('Name', size=255)

class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    @api.multi
    def invoice_litigation(self):
        for invoice in self:
            invoice.litigation = True

    @api.multi
    def invoice_problem_solving_in_progress(self):
        for invoice in self:
            invoice.problem_solving_in_progress = True
    
    @api.multi
    def invoice_problem(self):
        for invoice in self:
            #check reason and file
            if not invoice.supplier_invoice_file:
                raise ValidationError(_('please fill supplier invoice file'))
            
            #add compensation line
            difference = abs(invoice.check_total - invoice.amount_total)
            if difference >= (invoice.currency_id.rounding/2.0):
                account_id = invoice.journal_id.default_debit_account_id.id
                tax_ids = self.env["account.invoice.line"].onchange_account_id(None, invoice.partner_id.id, invoice.type, invoice.fiscal_position.id, account_id)['value']['invoice_line_tax_id']
                taxes = self.env["account.tax"].browse(tax_ids)
                tax_percent = 0
                
                for tax in taxes._unit_compute(taxes=taxes,price_unit=100.,partner=invoice.partner_id,quantity=1):
                    tax_percent = tax_percent + tax['amount']
                
                
                invoice_line = self.env["account.invoice.line"].create({
                        'quantity':1, 
                        'price_unit':difference/((tax_percent/100)+1), 
                        'name':'adjustment', 
                        'account_id':account_id, 
                        'invoice_id':invoice.id,
                        'invoice_line_tax_id':[(4,tax_id) for tax_id in tax_ids]
                    })
                
                invoice.button_reset_taxes()
                
            #validate invoice
            invoice.signal_workflow('invoice_open')
            
            #write values
            invoice.force_payment_sent = True
            invoice.validation_problem = True
            
        return True
    
    @api.multi
    def _get_purchase_type(self):
        res = {}
        for invoice in self:
            if invoice.purchase_ids and invoice.purchase_ids[0].purchase_type_id:
                invoice.purchase_type_id = invoice.purchase_ids[0].purchase_type_id.id
            else:
                invoice.purchase_type_id = None
        return res
                
    @api.multi      
    def _get_diff_supplier_due_date(self):
        res = {}
        for invoice in self:
            invoice.diff_supplier_due_date = (invoice.due_date_supplier != invoice.date_due)
        return res
    
    def onchange_name(self, cr, uid, ids, name, reference_type):
        res = {}
        if reference_type == 'none':
            res['value'] = {'reference':name}
        return res
    
    purchase_ids = fields.Many2many('purchase.order', 'purchase_invoice_rel', 'invoice_id', 'purchase_id', 'Purchases')
    validation_problem = fields.Boolean("Validation problem")
    validation_problem_type = fields.Many2one("account.invoice.validation.problem", "Problem type")
    litigation = fields.Boolean("Litigation")
    supplier_invoice_file = fields.Binary("Supplier invoice file")
    validation_problem_comment = fields.Text("Validation problem comment")
    due_date_supplier = fields.Date("Supplier due date")
    problem_amount = fields.Float("Problem amount")
    force_payment_sent = fields.Boolean("Do not appear in payment orders (problem)")
    purchase_type_id = fields.Many2one("purchase.order.type", compute='_get_purchase_type', string="Purchase type")
    diff_supplier_due_date = fields.Boolean(compute='_get_diff_supplier_due_date', string="Difference between supplier due date and due date", store=True)
    problem_solving_in_progress = fields.Boolean('Problem solving in progress')

class account_move_line(models.Model):
    _inherit = 'account.move.line'
    
    force_payment_sent = fields.Boolean(related="invoice.force_payment_sent", string="Do not appear in payment orders (problem)")
    
