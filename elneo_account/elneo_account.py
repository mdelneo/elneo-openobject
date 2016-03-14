# -*- coding: utf-8 -*-
from openerp import models,fields,api
from openerp.tools.float_utils import float_compare, float_round


JOURNAL_TYPE_MAP = {
    ('outgoing', 'customer'): ['sale'],
    ('outgoing', 'supplier'): ['purchase_refund'],
    ('outgoing', 'transit'): ['sale', 'purchase_refund'],
    ('incoming', 'supplier'): ['purchase'],
    ('incoming', 'customer'): ['sale_refund'],
    ('incoming', 'transit'): ['purchase', 'sale_refund'],
}

class account_payment_term(models.Model):
    _inherit = 'account.payment.term'
    
    alert = fields.Boolean('Alerte', help='Alert when confirm a sale order with this payment term')
    

class stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'
    
    @api.one
    def do_detailed_transfer(self):
        res = super(stock_transfer_details,self).do_detailed_transfer()
        if self.picking_id.invoice_state == '2binvoiced' and (self.picking_id.picking_type_id.code == 'incoming' or self.picking_id.picking_type_id.code == 'outgoing'):
            wizard = self.env['stock.invoice.onshipping'].with_context(active_ids=[self.picking_id.id]).create({})
            wizard.create_invoice()
        return res
    
    
class stock_move(models.Model):
    _inherit = 'stock.move'
    
    @api.model
    def _create_invoice_line_from_vals(self, move, invoice_line_vals):
        
            
        res = super(stock_move,self)._create_invoice_line_from_vals(move, invoice_line_vals)
        
        if res:
            invoice_line = self.env['account.invoice.line'].browse(res)
        if move.procurement_id and move.procurement_id.sale_line_id:
            invoice_line.cost_price = move.procurement_id.sale_line_id.purchase_price
        elif move.product_id:
            invoice_line.cost_price = move.product_id.cost_price
        return res
    
class stock_picking(models.Model):
    _inherit = 'stock.picking'
    
    def _get_invoice_vals(self, cr, uid, key, inv_type, journal_id, move, context=None):
        res = super(stock_picking,self)._get_invoice_vals(cr, uid, key, inv_type, journal_id, move, context=None)
        if move.picking_id.origin:
            origin = res['origin'] or ''
            res['origin'] = origin+move.picking_id.origin
        return res

class account_period(models.Model):
    _inherit = 'account.period'
    period_closed_qlikview = fields.Boolean('Period closed (Qlikview')


class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'
    
    @api.model
    def default_get(self, fields_list):
        res = super(account_invoice_line,self).default_get(fields_list)
        if 'name' in fields_list:
            res['name'] = '/'
        return res
    
    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_id', 'quantity',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id')
    def _compute_price(self):
        price = self.price_unit
        taxes = self.invoice_line_tax_id.compute_all(price, self.quantity, product=self.product_id, partner=self.invoice_id.partner_id)
        self.price_subtotal = taxes['total']
        if self.invoice_id:
            self.price_subtotal = self.invoice_id.currency_id.round(self.price_subtotal)
    
class account_invoice_tax(models.Model):
    _inherit = 'account.invoice.tax'
    
    @api.v8
    def compute(self, invoice):
        tax_grouped = {}
        currency = invoice.currency_id.with_context(date=invoice.date_invoice or fields.Date.context_today(invoice))
        company_currency = invoice.company_id.currency_id
        for line in invoice.invoice_line:
            taxes = line.invoice_line_tax_id.compute_all(
                (line.price_unit),
                line.quantity, line.product_id, invoice.partner_id)['taxes']
            for tax in taxes:
                val = {
                    'invoice_id': invoice.id,
                    'name': tax['name'],
                    'amount': tax['amount'],
                    'manual': False,
                    'sequence': tax['sequence'],
                    'base': currency.round(tax['price_unit'] * line['quantity']),
                }
                if invoice.type in ('out_invoice','in_invoice'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
                    val['base_amount'] = currency.compute(val['base'] * tax['base_sign'], company_currency, round=False)
                    val['tax_amount'] = currency.compute(val['amount'] * tax['tax_sign'], company_currency, round=False)
                    val['account_id'] = tax['account_collected_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_collected_id']
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = currency.compute(val['base'] * tax['ref_base_sign'], company_currency, round=False)
                    val['tax_amount'] = currency.compute(val['amount'] * tax['ref_tax_sign'], company_currency, round=False)
                    val['account_id'] = tax['account_paid_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_paid_id']

                # If the taxes generate moves on the same financial account as the invoice line
                # and no default analytic account is defined at the tax level, propagate the
                # analytic account from the invoice line to the tax line. This is necessary
                # in situations were (part of) the taxes cannot be reclaimed,
                # to ensure the tax move is allocated to the proper analytic account.
                if not val.get('account_analytic_id') and line.account_analytic_id and val['account_id'] == line.account_id.id:
                    val['account_analytic_id'] = line.account_analytic_id.id

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']

        for t in tax_grouped.values():
            t['base'] = currency.round(t['base'])
            t['amount'] = currency.round(t['amount'])
            t['base_amount'] = currency.round(t['base_amount'])
            t['tax_amount'] = currency.round(t['tax_amount'])

        return tax_grouped

class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    
    @api.multi
    def do_merge(self, keep_references=True, date_invoice=False):
        #keep picking_ids link when merge invoices
        res = super(account_invoice,self).do_merge(keep_references,date_invoice)
        for new_invoice_id in res:
            for old_invoice_id in res[new_invoice_id]:
                old_invoice = self.browse(old_invoice_id)
                old_invoice.internal_number = None
                pickings = self.env['stock.picking'].search([('invoice_id','=',old_invoice_id)])
                for picking in pickings:
                    picking.invoice_id = new_invoice_id
            
                    
            if 'sale.order' in self.env.registry:
                todos = self.env['sale.order'].search(
                    [('invoice_ids', 'in', res[new_invoice_id])])
                todos.write({'invoice_ids': [(4, new_invoice_id)]})
                for org_so in todos:
                    for so_line in org_so.order_line:
                        invoice_line_ids = self.env['account.invoice.line'].search(
                            [('product_id', '=', so_line.product_id.id),
                             ('invoice_id', '=', new_invoice_id)])
                        if invoice_line_ids:
                            so_line.write(
                                {'invoice_lines': [(6, 0, invoice_line_ids.mapped('id'))]})
            if 'purchase.order' in self.env.registry:
                todos = self.env['purchase.order'].search(
                    [('invoice_ids', 'in', res[new_invoice_id])])
                todos.write({'invoice_ids': [(4, new_invoice_id)]})
        return res
        
    
    @api.multi
    def test_virtual(self):
        return False
    
    @api.multi
    def write(self,vals):
        if vals.get('partner_id',False):
            self._onchange__partner_id()
        
        return super(account_invoice,self).write(vals)
    
    @api.model
    def create(self,vals):
            
        if vals.get('partner_id',False):
            partner = self.env['res.partner'].browse(vals.get('partner_id'))
            
            vals['_partner_id'] = partner.commercial_partner_id.id
            
        return super(account_invoice,self).create(vals)            
       
     
    @api.model
    def default_get(self, fields_list):
        res = super(account_invoice,self).default_get(fields_list)
        
        #set default value of date_invoice and period_id : set the same as last invoice encoded by current user
        if res.get('type','') == 'in_invoice':
            cr = self._cr
            last_in_invoice = None
            cr.execute("select id from account_invoice where type = 'in_invoice' and create_uid = "+str(self._uid)+" order by id desc limit 1")
            last_in_invoice_id = cr.fetchone()[0]
            last_in_invoice = self.env["account.invoice"].browse(last_in_invoice_id)
            
            if 'date_invoice' in fields_list and not 'date_invoice' in res:
                res['date_invoice'] = last_in_invoice.date_invoice
                
            if 'period_id' in fields_list and not 'period_id' in res:
                res['period_id'] = last_in_invoice.period_id.id
                
        return res
    
    @api.multi
    def _get_purchase_type(self):
        for invoice in self:
            if invoice.purchase_ids and invoice.purchase_ids[0].purchase_type_id:
                invoice.purchase_type_id = invoice.purchase_ids[0].purchase_type_id.id
            else:
                invoice.purchase_type_id = None
                
    @api.onchange('_partner_id')
    def _onchange__partner_id(self):
        if self._partner_id:
            if self.partner_id.commercial_partner_id != self._partner_id:
                invoices = self._partner_id.child_ids.filtered(lambda r:r.type == 'invoice')
                if invoices:
                    self.partner_id = invoices[0]
                else:
                    self.partner_id = self._partner_id
            
    
    @api.multi
    def onchange_partner_id(self, type, partner_id, date_invoice=False,
                            payment_term=False, partner_bank_id=False,
                            company_id=False):
        result = super(account_invoice, self).onchange_partner_id(
            type, partner_id, date_invoice, payment_term, partner_bank_id,
            company_id)
        if type == 'out_invoice' and partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            result['value']['_partner_id'] = partner.commercial_partner_id
        return result
    
    
    def _auto_init(self,cr,args):
        res = super(account_invoice, self)._auto_init(cr,args)
        
        '''UPDATE invoices that dont have _partner_id'''
        
        
        cr.execute('''UPDATE account_invoice ai SET _partner_id =
            (SELECT commercial_partner_id FROM res_partner WHERE id = ai.partner_id)
             WHERE _partner_id IS NULL''')
                
        return res      
    
    purchase_type_id = fields.Many2one(comodel_name='purchase.order.type', string='Purchase type', compute='_get_purchase_type', readonly=True)
    purchase_ids = fields.Many2many('purchase.order', 'purchase_invoice_rel', 'invoice_id', 'purchase_id', 'Purchases')
    partner_id = fields.Many2one(string="Invoice Address",index=True)
    _partner_id = fields.Many2one('res.partner',string="Partner",required=True,index=True,help="Partner to help selection of invoice address")
    
class ResPartner(models.Model):
    _inherit='res.partner'
    
    @api.model
    def _commercial_fields(self):
        res = super(ResPartner, self)._commercial_fields()
        if 'last_reconciliation_date' in res:
            res.remove('last_reconciliation_date')
        
        return res
    
