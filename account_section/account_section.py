# -*- coding: utf-8 -*-
from openerp import models,fields,api,osv
from datetime import datetime
from openerp.tools.translate import _

class crm_case_section(models.Model):
    _inherit = 'crm.case.section'
    
    sale_account_id = fields.Many2one('account.account', 'Sale account', required=False)
    purchase_account_id = fields.Many2one("account.account", string="Purchase account")
     

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    @api.multi
    def invoice_line_create(self):
        res = super(sale_order_line, self).invoice_line_create()
        if res and len(res)>0:
            invoiced_lines = {}
            for so_line in self:
                for invoice_line in so_line.invoice_lines:
                    if invoice_line.id in res:
                        account_id = so_line.order_id.section_id and so_line.order_id.section_id.sale_account_id.id
                        if account_id:        
                            if not invoiced_lines.has_key(account_id):
                                invoiced_lines[account_id] = [invoice_line]
                            else:
                                invoiced_lines[account_id].append(invoice_line)
            
            for account in invoiced_lines.keys():
                for invoiced_line in invoiced_lines[account]:
                    invoiced_line.account_id = account
                
        return res