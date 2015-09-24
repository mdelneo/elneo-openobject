from openerp import models, fields, api, _
from openerp.exceptions import RedirectWarning, Warning
from datetime import datetime

class purchase_order(models.Model):
    
    _inherit='purchase.order'
    
    user_amount_unblocked = fields.Many2one('res.users','Unblocked on Amount user',readonly=True)
    date_amount_unblocked=fields.Datetime('Unblocked on Amount date',readonly=True)
    
    @api.model
    # Add Workflow condition
    def check_amount_great(self):
        res = True
        
        purchase_validate_amount = self.env['ir.config_parameter'].get_param('elneo_purchase_validate_amount.purchase_validate_amount',False)
        
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

        return  self.warn_amount()

purchase_order()