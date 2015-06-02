from openerp import models, fields, api, _
import time
import datetime

class account_followup_semi(models.TransientModel):
    _name = 'account_followup.semi'
    _rec_name = 'date'
    _description = 'Semi Automatic Print Followup & Send Mail to Customers'
    
    
    #Get Followup from active_id or from user's company
    def _get_followup(self):
        if self.env.context.get('active_model', 'ir.ui.menu') == 'account_followup.followup':
            return self.env.context.get('active_id', False)
        
        company_id = self.env.user.company_id.id
        
        followp_id = self.env['account_followup.followup'].search([('company_id', '=', company_id)])
        return followp_id and followp_id[0] or False

    date = fields.Date('Follow-up Sending Date', required=True, help="This field allow you to select a forecast date to plan your follow-ups",default=lambda *a: time.strftime('%Y-%m-%d'))
    followup_id = fields.Many2one('account_followup.followup', 'Follow-up', required=True, default=_get_followup)

    #Go to next step
    @api.multi
    def do_continue(self):
        mod_obj = self.env['ir.model.data']
        
        #Get array from model
        data = self.read(self.ids)
        if (len(data) > 0):
            data = data[0]
        else:
            raise Warning(_('Error'),_('No Model found. Contact your Administrator'))
    
        data['followup_id'] = self.followup_id.id
        data['date'] = self.date
        
        model_data = mod_obj.search([('model','=','ir.ui.view'),('name','=','view_account_followup_print_semi')])
        resource = model_data.res_id
        
        context = self._context.copy()
        context.update({'followup_id': data['followup_id'], 'date':data['date']})
        
        return {
            'name': _('Select Partners'),
            'view_type': 'form',
            'context': context,
            'view_mode': 'tree,form',
            'res_model': 'account_followup.print',
            'views': [(resource,'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
            }


class account_followup_semi_print(models.TransientModel):
    #_name = "account_followup.print_semi"
    _inherit = 'account_followup.print'
    
    @api.multi
    def _get_date(self):
        
        the_date = time.strftime('%Y-%m-%d')
        
        if self.env.context.has_key('date') and self.env.context['date']:
            the_date = self.env.context['date']

        return the_date
    
    
    no_lit = fields.Boolean('No Litigations',help="No Litigations on reminders prints")
    date = fields.Date('Follow-up Sending Date', required=True, help="This field allow you to select a forecast date to plan your follow-ups",default=_get_date)
    
    @api.multi
    def clear_partners(self):
        self.write({'partner_ids':[(5,0)]})
        
        model_data = self.env['ir.model.data'].search([('model','=','ir.ui.view'),('name','=','view_account_followup_print_semi')])
        resource = model_data.res_id
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Order'),
            'res_model': 'account_followup.print',
            'res_id': self.ids[0], #If you want to go on perticular record then you can use res_id 
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': resource,
            'target': 'new',
            'nodestroy': True,
        }
    
    @api.multi
    def do_process(self):

        for wizard in self:
            continue
        
        to_update = self._get_moves_to_update()
        
        date = self.date
        
        data = self.read(self.ids)[0]
        data['date'] = date
        data['followup_id'] = wizard.followup_id.id

        #Update partners
        self.do_update_followup_level(to_update, self.partner_ids.mapped('id'), self.date)
        #process the partners (send mails...)
        restot = self.process_partners(self.partner_ids.mapped('id'), data)
        #context.update(restot_context)
        #clear the manual actions if nothing is due anymore
        nbactionscleared = self.clear_manual_actions(self.partner_ids.mapped('id'))
        if nbactionscleared > 0:
            restot['resulttext'] = restot['resulttext'] + "<li>" +  _("%s partners have no credits and as such the action is cleared") %(str(nbactionscleared)) + "</li>" 
        #return the next action
    
        
        mod_obj = self.env['ir.model.data']
        for model_data in mod_obj.search([('model','=','ir.ui.view'),('name','=','view_account_followup_sending_results')]):
            resource_id = model_data.res_id
            
        context = self._context.copy()
        context.update({'description': restot['resulttext'], 'needprinting': restot['needprinting'], 'report_data': restot['action']})
        return {
            'name': _('Send Letters and Emails: Actions Summary'),
            'view_type': 'form',
            'context': context,
            'view_mode': 'tree,form',
            'res_model': 'account_followup.sending.results',
            'views': [(resource_id,'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
            }
    
    #Get moves from chosen partners    
    def _get_moves_to_update(self):
        #BE CAREFULL : Partner ids are not res.partner ids !!!
        partner_list = self.env['account_followup.stat.by.partner'].browse(self.partner_ids.mapped('id')).mapped('partner_id')
        
        self.env.cr.execute(
            "SELECT l.partner_id, l.followup_line_id,l.date_maturity, l.date, l.id "\
            "FROM account_move_line AS l "\
                "LEFT JOIN account_account AS a "\
                "ON (l.account_id=a.id) "\
            "WHERE (l.reconcile_id IS NULL) "\
                "AND (a.type='receivable') "\
                "AND (l.state<>'draft') "\
                "AND (l.partner_id is NOT NULL) "\
                "AND (a.active) "\
                "AND (l.debit > 0) "\
                "AND (l.company_id = %s) " \
                "AND (l.blocked = False)" \
                "AND (l.partner_id IN %s)" \
            "ORDER BY l.date", (self.followup_id.company_id.id,tuple(partner_list.mapped('id'))))  #l.blocked added to take litigation into account and it is not necessary to change follow-up level of account move lines without debit
        move_lines = self.env.cr.fetchall()
        
        date = 'date' in self.env.context and self.env.context['date']
        
        current_date = datetime.date(*time.strptime(date,
            '%Y-%m-%d')[:3])
        self.env.cr.execute(
            "SELECT * "\
            "FROM account_followup_followup_line "\
            "WHERE followup_id=%s "\
            "ORDER BY delay", (self.followup_id.id,))
        
        fups = {}
        old = None
        
        #Create dictionary of tuples where first element is the date to compare with the due date and second element is the id of the next level
        for result in self.env.cr.dictfetchall():
            delay = datetime.timedelta(days=result['delay'])
            fups[old] = (current_date - delay, result['id'])
            old = result['id']
            
        partner_list = []
        to_update = {}
        
        #Fill dictionary of accountmovelines to_update with the partners that need to be updated
        for partner_id, followup_line_id, date_maturity,date, id in move_lines:
            if not partner_id:
                continue
            if followup_line_id not in fups:
                continue
            stat_line_id = partner_id * 10000 + self.followup_id.company_id.id
            if date_maturity:
                if date_maturity <= fups[followup_line_id][0].strftime('%Y-%m-%d'):
                    if stat_line_id not in partner_list:
                        partner_list.append(stat_line_id)
                    to_update[str(id)]= {'level': fups[followup_line_id][1], 'partner_id': stat_line_id}
            elif date and date <= fups[followup_line_id][0].strftime('%Y-%m-%d'):
                if stat_line_id not in partner_list:
                    partner_list.append(stat_line_id)
                to_update[str(id)]= {'level': fups[followup_line_id][1], 'partner_id': stat_line_id}
        
        return to_update
        
        
    #Change default function
    def _get_partners_followup(self):
        followup = None
        if self.env.context.has_key('followup_id'):
            followup = self.env['account_followup.followup'].browse(self.env.context['followup_id'])
            
        if followup is None :
            return None

        query = "SELECT l.partner_id, l.followup_line_id,l.date_maturity, l.date, l.id "\
            "FROM account_move_line AS l "\
                "LEFT JOIN account_account AS a "\
                "ON (l.account_id=a.id) "\
            "WHERE (l.reconcile_id IS NULL) "\
                "AND (a.type='receivable') "\
                "AND (l.state<>'draft') "\
                "AND (l.partner_id is NOT NULL) "\
                "AND (a.active) "\
                "AND (l.debit > 0) "\
                "AND (l.company_id = %s) " \
                "AND (l.blocked = False)" \
            "ORDER BY l.date"
        
        
        self.env.cr.execute(query, (followup.company_id.id,))  #l.blocked added to take litigation into account and it is not necessary to change follow-up level of account move lines without debit
        move_lines = self.env.cr.fetchall()
        old = None
        fups = {}
        fup_id = 'followup_id' in self.env.context and self.env.context['followup_id'] or followup.id
        date = 'date' in self.env.context and self.env.context['date']

        current_date = datetime.date(*time.strptime(date,
            '%Y-%m-%d')[:3])
        self.env.cr.execute(
            "SELECT * "\
            "FROM account_followup_followup_line "\
            "WHERE followup_id=%s "\
            "ORDER BY delay", (fup_id,))
        
        #Create dictionary of tuples where first element is the date to compare with the due date and second element is the id of the next level
        for result in self.env.cr.dictfetchall():
            delay = datetime.timedelta(days=result['delay'])
            fups[old] = (current_date - delay, result['id'])
            old = result['id']

        partner_list = []
        to_update = {}
        
        #Fill dictionary of accountmovelines to_update with the partners that need to be updated
        for partner_id, followup_line_id, date_maturity,date, id in move_lines:
            if not partner_id:
                continue
            if followup_line_id not in fups:
                continue
            stat_line_id = partner_id * 10000 + followup.company_id.id
            if date_maturity:
                if date_maturity <= fups[followup_line_id][0].strftime('%Y-%m-%d'):
                    if stat_line_id not in partner_list:
                        partner_list.append(stat_line_id)
                    to_update[str(id)]= {'level': fups[followup_line_id][1], 'partner_id': stat_line_id}
            elif date and date <= fups[followup_line_id][0].strftime('%Y-%m-%d'):
                if stat_line_id not in partner_list:
                    partner_list.append(stat_line_id)
                to_update[str(id)]= {'level': fups[followup_line_id][1], 'partner_id': stat_line_id}
        return {'partner_ids': partner_list, 'to_update': to_update}
    
    
    def _get_partners(self):
        partners = self._get_partners_followup()
        if partners is None:
            return
        
        return self._get_partners_followup()['partner_ids']
    
    @api.multi
    #Do manual printing for Semi Automatic followups
    def do_print(self):
        for wizard in self:
            action = self.env['res.partner'].do_partner_print(wizard.partner_ids.mapped('id'), {'no_litigation':wizard.no_lit,'date':wizard.date,'followup_id':wizard.followup_id.id})
    
            mod_obj = self.env['ir.model.data']
            for model_data in mod_obj.search([('model','=','ir.ui.view'),('name','=','view_account_followup_sending_results')]):
                resource_id = model_data.res_id
                
            description = _('Click on Download button below to get Followup file generated.')
            
            context = wizard._context.copy()
            context.update({'date':self.date,'description': description, 'needprinting': True, 'report_data': action or {}})
        return {
            'name': _('Send Letters : Actions Summary'),
            'view_type': 'form',
            'context': context,
            'view_mode': 'tree,form',
            'res_model': 'account_followup.sending.results',
            'views': [(resource_id,'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
            }

    
    partner_ids = fields.Many2many('account_followup.stat.by.partner', 'partner_stat_rel', 
                                        'osv_memory_id', 'partner_id', 'Partners', required=True,default=_get_partners)
