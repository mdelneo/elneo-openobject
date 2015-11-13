from openerp import models, fields, api, _

class sale_order(models.Model):
    _inherit='sale.order'
    
    partner_vat=fields.Char('Partner VAT',related='partner_id.vat',readonly=True,store=False)
    
    @api.multi
    def action_button_confirm(self):
        assert len(self) == 1, 'This option should only be used for a single id at a time.'
        mod_obj = self.env['ir.model.data']
        
        for sale in self:
            if not self._context.get('from_payment_term_wizard',False) and sale.payment_term and sale.payment_term.alert:
                model_data = mod_obj.search([('model','=','ir.ui.view'),('name','=','payment_term_wizard_form_view')])
                resource = model_data.res_id
                
                return {
                        'name': _('Payment term'),
                        'view_type': 'form',
                        'context': self._context,
                        'view_mode': 'form',
                        'res_model': 'payment.term.wizard',
                        'views': [(resource,'form')],
                        'nodestroy':True,
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                }
            else:
                return super(sale_order, self).action_button_confirm()
    
sale_order()    