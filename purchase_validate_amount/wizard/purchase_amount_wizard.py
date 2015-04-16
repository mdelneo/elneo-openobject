from openerp import models, fields, _, api
from openerp.exceptions import Warning
from openerp.tools.safe_eval import safe_eval
from datetime import datetime

class purchase_amount_wizard(models.TransientModel):
    _name = 'purchase.amount.wizard'
    _description = 'Purchase amount wizard'
    
    
    users_to_warn=fields.Many2many('res.users',string='Users To Warn')
    group_id=fields.Many2one('res.groups','Administrative Group')
    

    
    @api.model
    def default_get(self,fields):
        """
         To get default values for the object.
         @param fields: List of fields for which we want default values
         @return: A dictionary with default values for all field in ``fields``
        """
        res = super(purchase_amount_wizard, self).default_get(fields)
        
        purchase_validate_group = self.env['ir.config_parameter'].get_param('elneo_purchase_validate_amount.purchase_validate_group',False)
        
        res.update({'group_id':int(purchase_validate_group)})
    
        return res
    
    
    
    
    '''
    @api.model
    def fields_view_get(self,view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(purchase_validation_wizard, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if self.env.context and self.env.context.has_key('step') and self.env.context['step'] == 'warning':
            result['arch'] = '<form string="Warning">'
            result['arch'] += '<header><h3>Warning</h3></header>'
            
            for message in self.env.context.get('warning_message'):
                result['arch'] +='<p>'
                result['arch'] += '<label string="%s" colspan="4"/>'%(message.replace("\"", "&quot;"))
                result['arch'] += '<br />'
                result['arch'] +='</p>'
            
            result['arch'] += '<footer>'
            result['arch'] += '<button special="cancel" string="Ok" class="oe_highlight"/></footer></form>'
            
            
        if self.env.context and self.env.context.has_key('step') and self.env.context['step'] == 'warning_email':
            result['arch'] = '<form string="Warning">'
            result['arch'] += '<header><h3>Warning</h3></header>'
            for message in self.env.context.get('warning_message'):
                result['arch'] +='<p>'
                result['arch'] += '<label string="%s" colspan="4"/>'%(message.replace("\"", "&quot;"))
                result['arch'] += '<br />'
                result['arch'] +='</p>'
            result['arch'] += '<footer>'
            result['arch'] += '<button special="cancel" string="Close"/><button name="send_mail" type="object" string="Send email" class="oe_highlight"/></footer></form>'
            
        return result
    '''
    
    
    @api.multi
    def send_mail(self):
        
        
        if len(self.users_to_warn) > 0:
            
            email_template = self.env.ref('puchase_validate_amount.email_template_purchase_amount_validate')
            #email_template = self.browse(safe_eval(self.env['ir.config_parameter'].get_param('elneo_purchase_validate_amount.email_template_id','False')))
        
            
            if not email_template:
                raise Warning(_("No Email Template is defined. Contact your Administrator"))
            
            user = self.env['res.users'].browse(self.env.user)
            if not user.user_email:
                raise Warning(_("Please fill an email for user %s")%(user.name,))
        
            for order in self.env['sale.order'].browse(self.env.context.get('order_email')):
                order.confirmed_delivery_date = order.delivery_date
                values = self.env['email.template'].generate_email_batch(email_template.id, [order.id])
                values[order.id]['email_to']=order.partner_order_id.email
                values[order.id]['recipient_ids']=[(4, pid) for pid in values.get('partner_ids', list())]
                msg_id = self.env['mail.mail'].create(values[order.id])
        
                
        return True
    
            
        
purchase_amount_wizard()
