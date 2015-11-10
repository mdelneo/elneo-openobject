
from openerp import models, fields, api, _
from openerp.exceptions import Warning


class payment_term_wizard(models.TransientModel):
    _name = "payment.term.wizard"
    
    @api.model
    def default_get(self,fields):
        res = super(payment_term_wizard, self).default_get(fields)
        return res
    
    @api.multi
    def order_confirm(self):
        sale_order = self.env['sale.order'].browse(self.env.context.get('active_ids')[0])
        sale_order.with_context(from_payment_term_wizard=True).action_button_confirm()
        return {'type': 'ir.actions.act_window_close'}