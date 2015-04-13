from openerp import models, fields, api, _
from datetime import datetime, timedelta

class purchase_order(models.Model):
    
    _inherit='purchase.order'
    
    important_purchase = fields.Boolean('Important Purchase (Reminder)',readonly=False, states={'done':[('readonly',True)]},help='Mark as important purchase. A reminder will be sent to the purchase validator x days before order\'s end.')
    reminder_sent = fields.Boolean('Reminder Sent')
    
    
    @api.model
    def check_important(self):
        res = True
        delay = self.env['ir.config_parameter'].get_param('important_purchase.purchase_important_remind_delay',False)
        
        if not delay:
            delay = 7
        else:
            delay = int(delay)
            
        important_purchases = self.search([('important_purchase','=',True),
                                                                             ('state','in',('approved',)),
                                                                             ('reminder_sent','=',False),
                                                                             ('minimum_planned_date','<',((datetime.now() + timedelta(days=delay)).strftime('%Y-%m-%d')))],
                                                                     )
        
        #self.send_delivery_reminder(important_purchases)
        
        important_purchases.send_delivery_reminder()
        
        return res
    
    @api.one
    def send_delivery_reminder(self):
        res=True

        
        email_subject = _('Reminder Purchase Order %s') % self.name
        email_message_text = _('The Purchase Order %s requires your attention.\n\n \
                                             As it is a sensible purchase, please check the delivery date with the supplier.') % (self.name)
        email_message_html = _('The Purchase Order %s requires your attention.<br\><br\> \
                                             As it is a sensible purchase, please check the delivery date with the supplier.') % (self.name)
        if self.validator:
            mail = {
                'email_from':self.company_id.email, 
                'email_to':self.validator.email, 
                'subject':email_subject, 
                'body_text':email_message_text,
                'body_html':email_message_html,
                'res_id':self.id,
                'model':'purchase.order'
                #'account_id':1,
                }
            email_id = self.env['mail.mail'].create(mail)
            
            if email_id:   
                self.write({'reminder_sent':True})

        return res

purchase_order()