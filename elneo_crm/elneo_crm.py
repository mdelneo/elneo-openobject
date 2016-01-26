# -*- coding: utf-8 -*-
from openerp import models,fields,api,_
from openerp.exceptions import ValidationError
from openerp.exceptions import Warning
#from openerp.addons.mail.mail_thread import mail_thread
import re

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
    @api.cr_uid_ids_context
    def message_post(self, cr, uid, thread_id, body='', subject=None, type='notification',
                     subtype=None, parent_id=False, attachments=None, context=None,
                     content_subtype='html', **kwargs):
        if context is None:
            context = {}
        context['mail_post_autofollow'] = False
        context['mail_create_nosubscribe'] = True
        return super(mail_thread, self).message_post(cr, uid, thread_id, body=body, subject=subject, type=type,
                     subtype=subtype, parent_id=parent_id, attachments=attachments, context=context,
                     content_subtype=content_subtype, **kwargs)

class calendar_event_type(models.Model):
    _inherit = 'calendar.event.type'
    google_prefix = fields.Char('google_prefix')
     

class calendar_event(models.Model):
    _inherit = 'calendar.event'
    
    validated = fields.Boolean('Validated')
    
    
    @api.one
    @api.onchange('categ_ids')
    def update_name_categ(self):
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
        new_name = self.name
        #compute prefix
        if self.validated:
            prefix = '[V]'
        else:
            prefix = ''
            if '[V]' in new_name:
                new_name = ''.join(new_name.split('[V]'))
        self.name = prefix+new_name
    
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
                partner.title = partner.corportation_type
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
            
            if not partner.is_company or self._context.get('contact_display',False):
                name = name_add(name, partner.street)
                name = name_add(name, partner.street2)
                name = name_add(name, partner.zip)
                name = name_add(name, partner.city, ' ')
                name = name_add(name, partner.country_id.name)
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