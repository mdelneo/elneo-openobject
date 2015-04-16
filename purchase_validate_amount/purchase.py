from openerp import models, fields, api, _
from openerp.exceptions import RedirectWarning, Warning
from datetime import datetime

class purchase_order(models.Model):
    
    _inherit='purchase.order'
    
    amount_unblocked = fields.Boolean('Unblocked (on Amount)',readonly=False, states={'done':[('readonly',True)]},help='If the order is blocked on amount, unblock it')
    user_amount_unblocked = fields.Many2one('res.users','Unblocked on Amount user',readonly=True)
    date_amount_unblocked=fields.Datetime('Unblocked on Amount date',readonly=True)
    
    @api.model
    # Add Workflow condition
    def check_amount_great(self):
        res = True
        
        purchase_validate_amount = self.env['ir.config_parameter'].get_param('elneo_purchase_validate_amount.elneo_purchase_validate_amount',False)
        
        if purchase_validate_amount:
            amount=int(purchase_validate_amount)
        else:
            amount = False
            
        if self.amount_untaxed and amount:
            if self.amount_untaxed < amount:
                res = False
            if self.amount_untaxed >= amount:
                res = True    
                
        return res
    
    
    def check_amount_low(self):
        res = False
        
        purchase_validate_amount = self.env['ir.config_parameter'].get_param('elneo_purchase_validate_amount.elneo_purchase_validate_amount',False)
        
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
        
        purchase_validate_amount = self.env['ir.config_parameter'].get_param('elneo_purchase_validate_amount.elneo_purchase_validate_amount',False)
        
        if purchase_validate_amount:
            amount=int(purchase_validate_amount)
        else:
            amount = False
            
            
        if self.amount_untaxed and amount:
            if self.amount_untaxed >= amount:
                res =  {
    "type": "ir.actions.act_window",
    "res_model": "purchase.amount.wizard",
    "views": [[False, "form"]],
    
    "target": "new",
}
                
                
                
                
                return res
                raise Warning('The amount of this order is too high to be confirmed by you. Ask your manager to do it.',_('Purchase Order Amount too high'))
        
        
    
    @api.one
    def write(self,vals):
        if vals.has_key('amount_unblocked') and vals['amount_unblocked']:
            self.user_amount_unblocked = self.env.user
            self.date_amount_unblocked = datetime.now()
        
        return super(purchase_order,self).write(vals)

purchase_order()