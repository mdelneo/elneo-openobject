# -*- coding: utf-8 -*-
import logging
from openerp import models,fields,api
from openerp.exceptions import ValidationError
import re
import sys

class mail_thread(models.Model):
    _inherit = 'mail.thread'
    
    @api.model
    def message_process(self, model, message, custom_values=None,
                        save_original=False, strip_attachments=False,
                        thread_id=None):
        #incoming mails are process only if they are linked to a sale order or a purchase order
        res = None
        sales = self.env['mail.message'].find_sale_order(message)
        purchases = self.env['mail.message'].find_purchase_order(message)
        
        if not message or sales or purchases: 
            res = super(mail_thread,self).message_process(model, message, custom_values, save_original, strip_attachments, thread_id)
        return res
    
mail_thread()


class mail_message(models.Model):
    _inherit = 'mail.message'
    
    @api.model
    def find_sale_order(self, msg):
        res = []
        so_list = re.compile(r"SO[a-zA-Z0-9_]+").findall(msg)
        for so_name in so_list:
            for so in self.env['sale.order'].search([('name','=',so_name)]):
                res.append(so)
        return res
    
    @api.model
    def find_purchase_order(self, msg):
        res = []
        po_list = re.compile(r"PO[a-zA-Z0-9_]+").findall(msg)
        for po_name in po_list:
            for po in self.env['purchase.order'].search([('name','=',po_name)]):
                res.append(po)
        return res
                
    @api.model
    def create(self, vals):
        res = super(mail_message,self).create(vals)
        text_search = vals['subject']+' '+vals['body']
        
        for so in self.find_sale_order(text_search):
            res.write({'model':'sale.order','res_id':so.id})
                    
        for po in self.find_purchase_order(text_search):
            res.write({'model':'purchase.order','res_id':po.id})
        
        return res
    
mail_message()    