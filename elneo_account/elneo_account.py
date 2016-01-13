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
        if self.picking_id.invoice_state == '2binvoiced' and self.picking_id.picking_type_id.code == 'incoming' and self.picking_id.move_lines[0].location_id.usage == 'supplier':
            wizard = self.env['stock.invoice.onshipping'].with_context(active_ids=[self.picking_id.id]).create({})
            wizard.create_invoice()
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

class account_move_line(models.Model):
    _inherit = 'account.move.line'
    
    @api.multi
    def reconcile(self, type='auto', writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False):
        res = super(account_move_line,self).reconcile(type, writeoff_acc_id, writeoff_period_id, writeoff_journal_id)
        return res
    
account_move_line()

class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'
    
    @api.model
    def default_get(self, fields_list):
        res = super(account_invoice_line,self).default_get(fields_list)
        if 'name' in fields_list:
            res['name'] = '/'
        return res
    

class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
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
    
    purchase_type_id = fields.Many2one(comodel_name='purchase.order.type', string='Purchase type', compute='_get_purchase_type', readonly=True)
    purchase_ids = fields.Many2many('purchase.order', 'purchase_invoice_rel', 'invoice_id', 'purchase_id', 'Purchases')
    partner_id = fields.Many2one(string="Invoice Address",index=True)
    _partner_id = fields.Many2one('res.partner',string="Partner",required=True,index=True,help="Partner to help selection of invoice address")
    
account_invoice()

    