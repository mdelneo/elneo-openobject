from datetime import timedelta,date

from openerp import models,fields, api, _

class PaymentOrderCreate(models.TransientModel):
    _inherit = 'payment.order.create'
    
    due_date = fields.Date(default=lambda *a: (date(date.today().year, date.today().month,1)-timedelta(days=1)).strftime('%Y-%m-%d'))
    journal_id = fields.Many2one('account.journal', 'Journal', help="If empty, search on all journals", domain=[('type', 'in', ['purchase', 'sale_refund'])])
    partner_ids = fields.Many2many('res.partner','payment_order_create_partner_rel','payment_order_create_id','partner_id',domain=[('parent_id','=',False)],string='Supplier', help="If empty, search on all suppliers")
    number_start = fields.Char(string='Invoice number start', help="Invoice number from which we want to pay")
    number_end = fields.Char(string='Invoice number end', help="Invoice number to which we want to pay")
    without_litigation = fields.Boolean(string='Without litigations',default=True,help='Check this if you don t want to include litigations')
    
    
    @api.model
    def default_get(self,fields):
        res = super(PaymentOrderCreate, self).default_get(fields)
        lines = self.env.context.get('line_ids',False)
        if lines:
            res['entries'] = lines

        return res
    
    @api.multi
    def search_entries(self):
        
        for order_create in self:
            req = '''select line.id 
                    from account_move_line line 
                        left join account_account account on account.id = line.account_id 
                        left join account_invoice inv on line.move_id = inv.move_id
                        left join account_journal journal on line.journal_id = journal.id 
                        where 
                        (inv.force_payment_sent = False or inv.force_payment_sent is null) and 
                        line.reconcile_id is null and 
                        account.type in ('payable', 'receivable')                     
                         
                        and credit > 0
                        and (SELECT
                                CASE WHEN line.amount_currency < 0
                                    THEN - line.amount_currency
                                    ELSE line.credit
                                END - coalesce(sum(pl.amount_currency), 0)
                                FROM payment_line pl
                                INNER JOIN payment_order po ON (pl.order_id = po.id)
                                WHERE move_line_id = line.id
                                AND po.state != 'cancel'
                                ) > 0
                        '''
            if order_create.duedate:
                req = req + "and (date_maturity <= '"+order_create.duedate+"' or date_maturity is null) "
            if order_create.journal_id:
                req = req + 'and line.journal_id = '+str(order_create.journal_id.id)+' '
            else:
                req = req + "and journal.type in ('purchase', 'sale_refund') "
            if order_create.without_litigation:
                req = req + 'and line.blocked = False '
            if order_create.partner_ids:
                req = req + "and line.partner_id in ("+','.join([str(p.id) for p in order_create.partner_ids])+") "
            if order_create.number_start:
                req = req + " and number >= '%s'"%(order_create.number_start)
            if order_create.number_end:
                req = req + " and number <= '%s'"%(order_create.number_end)
                
            req = req + ' order by inv.number asc'
                
            self.env.cr.execute(req)
            line_ids = map(lambda x: x[0], self.env.cr.fetchall())

        
        model_data_ids = self.env['ir.model.data'].with_context(line_ids=line_ids).search([('model', '=', 'ir.ui.view'), ('name', '=', 'view_create_payment_order_lines')])
        resource_id = model_data_ids.read()[0]['res_id']
        
        context = self.env.context.copy()
        context.update({'line_ids': line_ids})
        
        return {'name': _('Populate Payment'),
                'context': context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'payment.order.create',
                'views': [(resource_id,'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
        }    