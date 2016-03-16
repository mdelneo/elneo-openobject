from openerp import models, fields, api, _
from openerp.exceptions import RedirectWarning, Warning
from datetime import datetime

class purchase_order(models.Model):
    
    _inherit='purchase.order'
    
    amount_unblocked_warned = fields.Boolean(string='Users warned to unblock',default=False,copy=False,help='Users that are in the amount approval group are warned to approve this order.')
    user_amount_unblocked = fields.Many2one('res.users','Unblocked on Amount user',readonly=True)
    date_amount_unblocked=fields.Datetime('Unblocked on Amount date',readonly=True)
    
    @api.model
    # Add Workflow condition
    def check_amount_great(self):
        res = True
        
        purchase_validate_amount = self.env['ir.config_parameter'].get_param('elneo_purchase_validate_amount.purchase_validate_amount',False)
        
        purchase_validate_group = int(self.env['ir.config_parameter'].get_param('elneo_purchase_validate_amount.purchase_validate_group',0))
        
        group = self.env['res.groups'].browse(purchase_validate_group)
        
        if purchase_validate_amount:
            amount=int(purchase_validate_amount)
        else:
            amount = False
            
        if self.amount_untaxed and amount:
            if self.amount_untaxed < amount:
                res = False
            if self.amount_untaxed >= amount:
                if group and self.env.user in group.users:
                    res = True
                else :
                    res=False
                    raise Warning(_('You cannot validate this purchase as you are not member of the validation group (%s)!') % group.name)
            
                
        return res
    
    
    def check_amount_low(self):
        res = True
        
        purchase_validate_amount = self.env['ir.config_parameter'].get_param('elneo_purchase_validate_amount.purchase_validate_amount',False)
        
        if purchase_validate_amount:
            amount=int(purchase_validate_amount)
        else:
            amount = False
            
            
        if self.amount_untaxed and amount:
            if self.amount_untaxed < amount:
                res = True
            if self.amount_untaxed >= amount:
                res=False

        return res
    
    def warn_amount(self):
        
        purchase_validate_amount = self.env['ir.config_parameter'].get_param('elneo_purchase_validate_amount.purchase_validate_amount',False)
        
        if purchase_validate_amount:
            amount=int(purchase_validate_amount)
        else:
            amount = False
            
            
        if self.amount_untaxed and amount:
            if self.amount_untaxed >= amount:
                return  {
                        "name":_("Purchase Amount Too High!"),
                    "type": "ir.actions.act_window",
                    "view_mode":"form",
                    "view_type":"form",
                    "res_model": "purchase.amount.wizard",
                    #"res_id":wizard_id,
                    "target": "new",
                    'nodestroy': True,
                    'active_ids':[self.id],
                        }
                
        return True
    
    @api.one
    def write(self,vals):
        
        if vals.has_key('state') and vals['state'] == 'approved':
            self.user_amount_unblocked = self.env.user
            self.date_amount_unblocked = datetime.now()
        
        return super(purchase_order,self).write(vals)
            
    
    @api.multi
    def elneo_purchase_confirm(self):
        res = False
        
        res = super(purchase_order,self).elneo_purchase_confirm()

        res = self.warn_amount()
        
        if not self.check_amount_low() and not self.amount_unblocked_warned:
            # Users to warn is void, send mail to everyone in the group
            purchase_validate_group = self.env['ir.config_parameter'].get_param('elneo_purchase_validate_amount.purchase_validate_group',False)
        
            group = self.env['res.groups'].browse(int(purchase_validate_group))
            
            if group.users:
                email_template = self.env.ref('elneo_purchase_validate_amount.email_template_purchase_amount_validate')
                values = self.env['email.template'].generate_email_batch(email_template.id, [self.id])
                values[self.id]['email_to']=','.join(group.users.mapped('partner_id.email'))
                values[self.id]['recipient_ids']=[(4, pid) for pid in group.users.mapped('partner_id.id')]
                msg_id = self.env['mail.mail'].create(values[self.id])
                self.amount_unblocked_warned = True
        
        return res

purchase_order()