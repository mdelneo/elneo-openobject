# -*- coding: utf-8 -*-
from openerp import models,fields,api,_
from openerp.exceptions import ValidationError
from openerp.exceptions import Warning
from openerp.addons.mail.mail_thread import mail_thread
import re
from datetime import datetime, timedelta
import time
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

'''
!!! ATTENTION !!!
dans module google_calendar : google_calendar.py
Fonction update_events
dans le paragraphe DO ACTION
avant : new_google_event_id = event.GG.event['id'].rsplit('_', 1)[1]

parfois event.GG.event['id'] ne contient pas '_' (notamment pour les evenements récurrents, chez certaines personnes

il faut donc rajouter les lignes suivantes avant : 

                        if '_' not in event.GG.event['id']:
                            continue
                        new_google_event_id = event.GG.event['id'].rsplit('_', 1)[1]
                        
(ligne 855)                        
'''


class mail_mail(models.Model):
    
    _inherit = 'mail.mail'
    
    @api.multi
    def send(self,auto_commit=False,raise_exception=False):
        if self.env['production.server'].is_production_server():
            return super(mail_mail,self).send(auto_commit=auto_commit,raise_exception=raise_exception)
        return True


class mail_compose_message(models.TransientModel):
    _inherit = 'mail.compose.message'
    
    
    @api.multi
    def send_mail(self):
        res = super(mail_compose_message,self).send_mail()

        for wizard in self:
            mass_mode = wizard.composition_mode in ('mass_mail', 'mass_post')
            active_model_pool = self.pool[wizard.model if wizard.model else 'mail.thread']
            if not hasattr(active_model_pool, 'message_post'):
                self = self.with_context(thread_model=wizard.model) 
                active_model_pool = self.env['mail.thread']

            # wizard works in batch mode: [res_id] or active_ids or active_domain
            if mass_mode and wizard.use_active_domain and wizard.model:
                res_ids = self.pool[wizard.model].search(eval(wizard.active_domain))
            elif mass_mode and wizard.model and self._context.get('active_ids'):
                res_ids = self._context['active_ids']
            else:
                res_ids = [wizard.res_id]

            batch_size = int(self.sudo().env['ir.config_parameter'].get_param('mail.batch_size')) or self._batch_size
            sliced_res_ids = [res_ids[i:i + batch_size] for i in range(0, len(res_ids), batch_size)]
            
            for res_ids in sliced_res_ids:
                all_mail_values = self.get_mail_values(wizard, res_ids)
                for res_id, mail_values in all_mail_values.iteritems():
                    mail_values['body_html'] = mail_values['body']
                    mail_values['reply_to'] = None
                    mail_values['email_to'] = ','.join([p.email for p in self.env['res.partner'].browse(mail_values['partner_ids'])])
                    servers = self.env['ir.mail_server'].search([('smtp_user','=',mail_values['email_from'])])
                    if servers:
                        mail_values['mail_server_id'] = servers[0].id
                    mail_values['attachment_ids'] = [(4,a) for a in mail_values['attachment_ids']]
                    self.env['mail.mail'].create(mail_values)
                    
        return res
    

class mail_followers(models.Model):
    _inherit = 'mail.followers'
    
    @api.model
    def create(self, vals):
        res = super(mail_followers,self.with_context(NewMeeting=True)).create(vals)
        return res

class crm_case_section(models.Model):
    _inherit = 'crm.case.section'
    
    administrative_user_id = fields.Many2one('res.users', string="Administrative")

class mail_thread(models.AbstractModel):
    _inherit='mail.thread'
    """ Disable autofollow
    """
    '''
    @api.multi
    def message_post(self, body='', subject=None, type='notification',
                     subtype=None, parent_id=False, attachments=None,
                     content_subtype='html', **kwargs):
        #if context is None:
        #    context = {}
        
        return super(MailThread, self.with_context(mail_post_autofollow=False,mail_create_nosubscribe=True)).message_post( body=body, subject=subject, type=type,
                     subtype=subtype, parent_id=parent_id, attachments=attachments,
                     content_subtype=content_subtype, **kwargs)
    '''
    
    @api.cr_uid_ids_context
    def message_post(self, cr, uid, thread_id, body='', subject=None, type='notification',subtype=None, parent_id=False, attachments=None, context=None,content_subtype='html', **kwargs):
        if context is None:
            context = {}
        new_context = context.copy()
        new_context['mail_post_autofollow'] = False
        new_context['mail_create_nosubscribe'] = True
        return super(mail_thread, self).message_post(cr, uid, thread_id,body=body, subject=subject, type=type,
                     subtype=subtype, parent_id=parent_id, attachments=attachments, context=new_context,
                     content_subtype=content_subtype,**kwargs)
    
    
    
class calendar_event_type(models.Model):
    _inherit = 'calendar.event.type'
    google_prefix = fields.Char('google_prefix')
     
def calendar_id2real_id(calendar_id=None, with_date=False):
    """
    Convert a "virtual/recurring event id" (type string) into a real event id (type int).
    E.g. virtual/recurring event id is 4-20091201100000, so it will return 4.
    @param calendar_id: id of calendar
    @param with_date: if a value is passed to this param it will return dates based on value of withdate + calendar_id
    @return: real event id
    """
    if calendar_id and isinstance(calendar_id, (basestring)):
        res = calendar_id.split('-')
        if len(res) >= 2:
            real_id = res[0]
            if with_date:
                real_date = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT, time.strptime(res[1], "%Y%m%d%H%M%S"))
                start = datetime.strptime(real_date, DEFAULT_SERVER_DATETIME_FORMAT)
                end = start + timedelta(hours=with_date)
                return (int(real_id), real_date, end.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            return int(real_id)
    return calendar_id and int(calendar_id) or calendar_id

class calendar_event(models.Model):
    _inherit = 'calendar.event'
    
    validated = fields.Boolean('Validated')
    
    partner_id = fields.Many2one('res.partner',string="Partner",domain="[('parent_id','=',False)]")
    partner_contact_id = fields.Many2one('res.partner',string="Partner Contact",domain="['|','&',('parent_id','=',False),('id','=',partner_id),('parent_id','=',partner_id)]")
    
    
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.partner_id and self.partner_contact_id:
            if self.partner_contact_id.parent_id != self.partner_id.parent_id:
                self.partner_contact_id = None
                
    @api.onchange('partner_contact_id')
    def onchange_partner_contact_id(self):
        if self.partner_contact_id and self.partner_contact_id.contact_address:
            # We take the display address and remove the carriage returns
            self.location = self.partner_contact_id.contact_address.replace('\n',' ')
            
            
        # We update the name of the meeting
        if self.partner_contact_id:
            name = ''
            if self.partner_contact_id.parent_id:
                name = '['+ self.partner_contact_id.parent_id.name + ']'
            if self.partner_contact_id.name:
                name += '['+ self.partner_contact_id.name + ']'
            if self.partner_contact_id.mobile:
                name += '['+self.partner_contact_id.mobile + ']'
            if self.partner_contact_id.phone:
                name += '['+self.partner_contact_id.phone + ']'
                
            if name:
                self.name = name
            
    
    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        if context is None:
            context = {}
        fields2 = fields and fields[:] or None
        EXTRAFIELDS = ('class', 'user_id', 'duration', 'allday', 'start', 'start_date', 'start_datetime', 'rrule')
        for f in EXTRAFIELDS:
            if fields and (f not in fields):
                fields2.append(f)
        if isinstance(ids, (basestring, int, long)):
            select = [ids]
        else:
            select = ids
        select = map(lambda x: (x, calendar_id2real_id(x)), select)
        result = []
        real_data = super(models.Model, self).read(cr, uid, [real_id for calendar_id, real_id in select], fields=fields2, context=context, load=load)
        real_data = dict(zip([x['id'] for x in real_data], real_data))

        for calendar_id, real_id in select:
            if real_id not in real_data:
                continue
            res = real_data[real_id].copy()
            ls = calendar_id2real_id(calendar_id, with_date=res and res.get('duration', 0) > 0 and res.get('duration') or 1)
            if not isinstance(ls, (basestring, int, long)) and len(ls) >= 2:
                res['start'] = ls[1]
                res['stop'] = ls[2]

                if res['allday']:
                    res['start_date'] = ls[1]
                    res['stop_date'] = ls[2]
                else:
                    res['start_datetime'] = ls[1]
                    res['stop_datetime'] = ls[2]

                if 'display_time' in fields:
                    res['display_time'] = self._get_display_time(cr, uid, ls[1], ls[2], res['duration'], res['allday'], context=context)

            res['id'] = calendar_id
            result.append(res)

        for r in result:
            if r['user_id']:
                user_id = type(r['user_id']) in (tuple, list) and r['user_id'][0] or r['user_id']
                if user_id == uid:
                    continue
            if r['class'] == 'private':
                for f in r.keys():
                    if f not in ('id', 'allday', 'start', 'stop', 'duration', 'user_id', 'state', 'interval', 'count', 'recurrent_id_date', 'rrule'):
                        if isinstance(r[f], list):
                            r[f] = []
                        else:
                            r[f] = False
                    if f == 'name':
                        r[f] = _('Busy')

        for r in result:
            for k in EXTRAFIELDS:
                if (k in r) and (fields and (k not in fields)):
                    del r[k]
        if isinstance(ids, (basestring, int, long)):
            return result and result[0] or False
        return result
    
    @api.one
    def _remove_categs_in_name(self):
        if self.name:
            for categ in self.env['calendar.event.type'].search([('google_prefix','!=',False)]):
                place = self.name.find('[' + categ.google_prefix + ']')
                if place != -1:
                    self.name = self.name.replace('['+categ.google_prefix+']','',1)
    
    @api.one
    @api.onchange('categ_ids')
    def update_name_categ(self):
        
        
        self._remove_categs_in_name()
        
        new_name = self.name
        for categ in self.categ_ids:
            if categ.google_prefix:
                prefix = '[' + str(categ.google_prefix) + ']'
                if categ.google_prefix:
                    if (categ.id in [c.id for c in self.categ_ids]):
                        new_name = prefix+new_name
                    else:
                        new_name = ''.join(new_name.split(prefix))
                    
        self.name = new_name
        
    @api.one
    @api.onchange('validated')
    def update_name_validated(self):
        if not self.name:
            self.name = ''
        new_name = self.name
        #compute prefix
        if self.validated:
            prefix = '[V]'
        else:
            prefix = ''
            if '[V]' in new_name:
                new_name = ''.join(new_name.split('[V]'))
        self.name = prefix+new_name
    
    '''
    @api.one
    @api.onchange('partner_ids')
    def update_name(self):
        if self.name:
            name = self.name
        else:
            name = ''
            
        address = ''
        prefix = ''
        
        for p in self.partner_ids:
            if len(self.env['res.users'].search([('partner_id','=',p.id)])) > 0:
                continue
            if p.commercial_partner_id and p.commercial_partner_id.id != p.id and p.commercial_partner_id.name:
                prefix = prefix + p.commercial_partner_id.name+' '
            if p.name:
                prefix = prefix + p.name
            #set address
            if p.street:
                address = address+p.street+' '
            if p.city:
                address = address+p.city+' '
            if p.mobile:
                address = address+p.mobile+' '
            elif p.phone:
                address = address+p.phone+' '
                
        self.location = address[:-2]
         
        prefix = prefix + ' ~ '
                
        #keep original name
        if ' ~ ' in name:
            name = name[name.rfind(' ~ ')+3:]
        
        #add prefix
        self.name = prefix+name
    '''
        

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    ref = fields.Char('Reference', size=10,index=True, readonly=True)
    alias = fields.Char('Alias', size=255,index=True)
    sales_count = fields.Integer('Number of sales', compute='_get_sales_count')
    type = fields.Selection([('contact', 'Contact'),('delivery', 'Shipping'), ('invoice', 'Invoice')], string='Address Type')
    property_account_position = fields.Many2one(required=True)
    title = fields.Many2one('res.partner.title', compute='get_title')
    corporation_type = fields.Many2one('res.partner.title', domain=[('domain','=','partner')])
    contact_title = fields.Many2one('res.partner.title', domain=[('domain','=','contact')])
    meeting_count = fields.Integer(compute='_meeting_count', string="# Meetings")
    use_parent_name = fields.Boolean('Use parent name')
    
    @api.multi
    def _meeting_count(self):
        def count_p(p):
            total = len(p.meeting_ids)
            if len(p.child_ids) > 0:
                for c in p.child_ids:
                    total = total + count_p(c)
            return total
        for partner in self:
            partner.meeting_count = count_p(partner)
            
            
    
    @api.multi
    def get_title(self):
        for partner in self:
            if partner.is_company:
                partner.title = partner.corporation_type
            else:
                partner.title = partner.contact_title
    
    @api.multi
    def name_get(self):
        def name_add(name, add, sep=', '):
            if not name:
                name = ''
            elif add:
                name = name+sep
            if add:
                name = name + add
            return name
            
        result = []
        for partner in self:
            
            name = ''
            if not partner.is_company and self.env.context.get('show_parent',False):
                name = name_add(name, partner.parent_name)
            name = name_add(name, partner.name)
            
            if not self.env.context.get('show_email',False) and not partner.is_company or self._context.get('contact_display',False):
                name = name_add(name, partner.street)
                name = name_add(name, partner.street2)
                name = name_add(name, partner.zip)
                name = name_add(name, partner.city, ' ')
                name = name_add(name, partner.country_id.name)
            elif self.env.context.get('show_email',False):
                if not partner.is_company and partner.parent_id and partner.parent_id.name:
                    name = name_add(name,partner.parent_id.name)
                name += partner.email and ('<%s>' % partner.email) or '<%s>' % (_('NO EMAIL'))
                
            else:
                name = name_add(name, partner.city)
                name = name_add(name, partner.vat)
            
            result.append((partner.id, name))
            
        return result

    
    
    @api.one
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = {} if default is None else default.copy()
        default.update({
            'vat': False,
            'name': (self.name or '') + ' (copy)',
            'ref': (self.name or '') + ' copy',
            })
        return super(res_partner, self.with_context(copy=True)).copy(default)
    
    @api.multi
    def write(self, vals):
        if not vals.get('active',True):
            sales = self.env['sale.order'].search([('partner_id','=',self.id),('state','not in',['cancel','done'])])
            if sales:
                raise Warning(_('There is few sales for this partner. Please close or cancel them before disable the partner.'))            
        return super(res_partner,self).write(vals)
    
    
    def action_view_sales(self, cr, uid, ids, context=None):
        result = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'sale.action_orders', raise_if_not_found=True)
        result = self.pool['ir.actions.act_window'].read(cr, uid, [result], context=context)[0]
        result['domain'] = "[('partner_id','in',[" + ','.join(map(str, ids)) + "])]"
        result['context'] = {'search_default_my_sale_orders_filter': 0}
        return result
    
    def _get_sales_count(self):
        self._cr.execute('select partner_id, count(id) from sale_order where partner_id in %s group by partner_id',(tuple([p.id for p in self]),))
        req_res = self._cr.fetchall()
        res = {}
        for req_res_line in req_res:
            res[req_res_line[0]] = req_res_line[1]
        for partner in self:
            if partner.id in res:
                partner.sales_count = res[partner.id]
            else:
                partner.sales_count = 0
        return res
            
    '''
    @api.constrains('vat')
    def _check_unique_vat(self):
        if self._context.get('copy',False):
            return True
        
        for partner in self:
            if partner.is_company and partner.vat:
                sames = self.search([('active','=',True),('parent_id','=',False),('id','!=',self.id),('vat','=',self.vat)])
                if (sames):
                    raise ValidationError("There is partner with the same VAT ! Please change it or go to the good partner.\n\n%s" % (sames[0].name))
        return True
    '''
    
    @api.constrains('ref')
    def _check_ref(self):
        if self._context.get('copy',False):
            return True
        
        #Mother companies must have reference
        if (not self.parent_id and not self.ref):
            raise ValidationError("You must fill in the reference for this partner!")
        
        if self.ref:
            sames = self.search([('active','=',True),('parent_id','=',False),('id','!=',self.id),('ref','=',self.ref)])
            
            if (sames):
                raise ValidationError("There is partner with the same reference! Please change it or go to the good partner.\n\n%s" % (sames[0].name))
            
            if len(re.compile(r"[a-zA-Z0-9_]+").findall(self.ref)) != 1:
                raise ValidationError(_('Special characters are not allowed on partner reference.'))
            
    
    @api.constrains('name')
    def _check_name(self):
        return True
        
        if self._context.get('copy',False) or self._context.get('NewMeeting',False):
            return True
        
        #Mother companies must have name
        if (not self.parent_id and not self.name):
            raise ValidationError("You must fill in the name for partner '%s' !"%(str(self.id),))
        
        if self.name and self.is_company:
            self._cr.execute('select id from res_partner where active = True and parent_id is null and id != %s and upper(name) = %s',(self.id,self.name.upper()))
            
            for t in self._cr.fetchall():
                raise ValidationError("There is partner with the same name! Please change it or go to the good partner.\n\n%s" % (self.browse(t[0]).name))
            
            
    def _get_default_is_company(self):
        return self._context.get('force_is_company', False)
    
    
    @api.multi
    def _sale_order_count(self):
        for partner in self:
            if not partner.is_company:
                partner.sale_order_count = 0
            else:
                count = self.env['sale.order'].search_count([('partner_id','=',partner.id),('state','not in',['cancel','draft'])])
                count_progress = self.env['sale.order'].search_count([('partner_id','=',partner.id),('state','not in',['cancel','draft','done'])])
                partner.sale_order_count = str(count)+' ('+str(count_progress)+')'
            
            
    @api.multi
    def _purchase_order_count(self):
        for partner in self:
            if not partner.is_company:
                partner.purchase_order_count = 0
            else:
                count = self.env['purchase.order'].search_count([('partner_id','=',partner.id),('state','not in',['cancel','draft'])])
                count_progress = self.env['purchase.order'].search_count([('partner_id','=',partner.id),('state','not in',['cancel','draft','done'])])
                partner.purchase_order_count = str(count)+' ('+str(count_progress)+')'
            
            
    @api.multi
    def _supplier_invoice_count(self):
        for partner in self:
            if not partner.is_company:
                partner.supplier_invoice_count = 0
            else:
                count = self.env['account.invoice'].search_count([('type','=','in_invoice'),('partner_id','=',partner.id),('state','not in',['cancel'])])
                count_progress = self.env['account.invoice'].search_count([('type','=','in_invoice'),('partner_id','=',partner.id),('state','not in',['cancel','open','paid'])])
                partner.supplier_invoice_count = str(count)+' ('+str(count_progress)+')'
            

    sale_order_count = fields.Char(compute='_sale_order_count', string='# of Sales Order', size=255)
    is_company = fields.Boolean('Is a company', default=_get_default_is_company)
    purchase_order_count = fields.Char(compute='_purchase_order_count', string='# of Purchase Order', size=255)
    supplier_invoice_count = fields.Char(compute='_supplier_invoice_count', string='# Supplier Invoices', size=255)