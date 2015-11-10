# -*- coding: utf-8 -*-
from openerp import models,fields,api
from openerp.tools.float_utils import float_compare, float_round

class account_payment_term(models.Model):
    _inherit = 'account.payment.term'
    
    alert = fields.Boolean('Alerte', help='Alert when confirm a sale order with this payment term')


class stock_move(models.Model):
    _inherit = 'stock.move'
    
    @api.multi
    def action_done(self):
        res = super(stock_move,self).action_done()
        
        pickings = set()
        for move in self:
            pickings.add(move.picking_id)
            
        for picking in pickings:
            if picking.picking_type_id.code == 'incoming':
                journal = self.env['account.invoice'].with_context(type='in_invoice')._default_journal()
                picking.action_invoice_create(journal_id=journal.id, group=False, type="in_invoice")
                
        return  res
    
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
    
    purchase_type_id = fields.Many2one('purchase.order.type', 'Purchase type', compute='_get_purchase_type', readonly=True)
    purchase_ids = fields.Many2many('purchase.order', 'purchase_invoice_rel', 'invoice_id', 'purchase_id', 'Purchases')
    
account_invoice()