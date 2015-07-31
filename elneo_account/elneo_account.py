# -*- coding: utf-8 -*-
from openerp import models,fields,api
from openerp.tools.float_utils import float_compare, float_round

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
    
account_invoice()