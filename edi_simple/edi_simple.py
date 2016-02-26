from openerp.tools import html_email_clean
from datetime import datetime
import logging
from xml.dom import ValidationErr
_logger = logging.getLogger(__name__)

from openerp import models, fields, api, _
from openerp.exceptions import Warning, ValidationError

class EDIImportScheduler(models.TransientModel):
    _name='edi.import.scheduler'
    
    @api.model
    def import_messages(self):
        for processor in self.env['edi.processor'].search([('active','=',True)]):
            processor.import_messages()
        
class EDIProcessScheduler(models.TransientModel):
    _name='edi.process.scheduler'
    
    @api.model
    def process_messages(self):
        for processor in self.env['edi.processor'].search([('active','=',True)]):
            processor.process_messages()

class EDIExport(models.AbstractModel):
    _name='edi.export'
    
    @api.one
    def simple_edi_export(self):
        
        
        return True
    
    @api.multi
    def button_simple_edi_export(self):
        
        for exporter in self:
            exporter.simple_edi_export()
        
        return True

class EDIProcessorLog(models.Model):
    _name = 'edi.processor.log'
    
    processor_id=fields.Many2one('edi.processor','Processor')
    date = fields.Datetime(string='Date')
    type=fields.Selection([('info','Info'),('warning','Warning'),('error','Error')],string='Type')
    log = fields.Text(string='Log')
    
    log_summary=fields.Char(compute='_get_log_summary',string='Summary')
    
    @api.one
    def _get_log_summary(self):
        if self.log:
            self.log_summary = self.log[:20]
        if len(self.log) > 20:
            self.log_summary += '(...)'
    
class EDIProcessor(models.Model):
    _name='edi.processor'
    
    name = fields.Char(string='Name',required=True)
    processor_type = fields.Selection([('dummy','Dummy')],required=True,default='dummy')
    active = fields.Boolean(string='Active')
    priority=fields.Integer(string='Priority',help='Define here the priority the processor has. The execution will order them')
    message_type_ids=fields.One2many('edi.message.type','processor',string='Message Types',help='The messages types linked to this processor')
    partner_ids = fields.Many2many('res.partner','edi_processor_res_partner_rel','processor_id','partner_id',string='Dependent partners',help='This is used to link specific partners to this edi processor')
    log_ids = fields.One2many('edi.processor.log','processor_id',string='Logs')
    
    send_error_users = fields.Many2many('res.users','edi_processor_error_users_rel','processor_id','user_id',string='Send Errors To')
    send_warning_users = fields.Many2many('res.users','edi_processor_warning_users_rel','processor_id','user_id',string='Send Warning To')
    
    @api.one
    @api.constrains('message_type_ids')
    def constraint_message_type_ids(self):
        check={}
        for message_type in self.message_type_ids:
            if check.has_key(message_type.usage) and check[message_type.usage] == True:
                raise ValidationError(_('The edi processor %s uses already the message type usage %s. Please choose another one!') % (self.name,message_type.usage))
            else:
                check[message_type.usage] = True
        
        return True
    
    @api.one
    def edi_log(self,log_type='info',log='',date=None):
        if not date:
            date = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        values = {
                  'type' : log_type,
                  'log' : log,
                  'date' : date,
                  'processor_id' : self.id
                  }
        
        self.env['edi.processor.log'].create(values)
        
        return True
    


    @api.model
    def import_messages(self):
        '''
        Function to import and create edi messages
        Need to be overridden by new modules
        '''
        return True
    
    @api.multi
    def pre_process_messages(self):
        '''
        Function to treat messages that are in draft and to confirm them
        '''
        for message in self.env['edi.message'].search([('state','in',['draft']),('processor','=',self.id)]):
            message.action_confirm()
            
        return True
    
    @api.model
    def _process(self,messages):
        return True
    
    @api.multi
    def process_messages(self):
        
        messages = self.env['edi.message'].search([('state','in',['confirmed']),('type.processor','=',self.id)])
        
        if self._process(messages):
            messages.action_done()
            
        return True
        

class EDIThread(models.AbstractModel):
    _name='edi.thread'
    
    edi_message_ids = fields.One2many('edi.message', 'res_id',
            domain=lambda self: [('model', '=', self._name)],
            auto_join=True,
            string='EDI Messages',
            help="EDI messages history")
    
    
    def get_edi_messages(self):
        return True
    
    @api.one
    def _get_edi_values(self):
        return {}
    
    @api.one
    @api.returns('edi.message')
    def edi_simple_create(self):
        values = self._get_edi_values()
        
        message = self.env['edi.message'].create(values)
        
        return message

class EDIMessage(models.Model):
    _name='edi.message'
    _inherit = ['mail.thread','ir.needaction_mixin']
    
    _message_read_limit = 30
    
    name = fields.Char('Name', required=True, index=True,default=lambda r:r.env['ir.sequence'].get('edi.message.seq'))
    type = fields.Many2one('edi.message.type',string='EDI Message Type',required=True)
    state = fields.Selection([('draft','Draft'),('confirmed','Confirmed'),('done','Done'),('warning','Warning'),('error','Error')],required=True,track_visibility='onchange',default='draft')
    origin = fields.Char(string='Origin', index=True)
    
    attachment_ids=fields.One2many(compute='_get_attachments',string='Attachments',comodel_name='ir.attachment')
    notification_ids = fields.One2many('mail.notification', 'message_id',string='Notifications', auto_join=True,help='Technical field holding the message notifications. Use notified_partner_ids to access notified partners.')
    confirmed_date = fields.Datetime('Confirmed Date')
    model = fields.Char('Related Document Model', size=128)
    res_id = fields.Integer('Related Document ID')
    
    error_report_sent = fields.Boolean('Error report sent',default=False)
    warning_report_sent = fields.Boolean('Warning report sent',default=False)
    
    
    @api.one
    def send_error_report(self):
        '''
        To be implemented
        '''
        self.error_report_sent = True
        
        return True
    
    @api.one
    def send_warning_report(self):
        '''
        To be implemented
        '''
        self.warning_report_sent = True
        
        return True
    
    @api.one
    def _get_attachments(self):
        self.attachment_ids = self.env['ir.attachment'].search([('res_model','=',self._name),('res_id','=',self.id)]).mapped('id')
        
        return True
    
    @api.multi
    def process(self):
        for message in self:
            if self.state == 'confirmed' and self.type and self.type.processor:
                self.type.processor.process(message)
    
    '''
    @api.model
    def create(self,vals):
        
        vals['name'] = self.env['ir.sequence'].get('edi.message.seq')
        if vals['name'] == False:
            raise Warning(_('The name of the EDI Message is not defined. Maybe the sequence is not well set.'))
        
        return super(EDIMessage,self).create(vals)
        
    '''
    
    @api.multi
    def action_draft(self):
        for message in self:
            message.state = 'draft'
        
        return True
            
    
    @api.multi
    def action_confirm(self):
        for message in self:
            message.state = 'confirmed'
            
        return True
    
    @api.multi
    def action_done(self):
        '''
        Function to treat messages that are confirmed and filtered by processor 'dummy'
        New modules have to change the search filter
        '''
        for message in self.filtered(lambda r:r.state == 'confirmed' and r.type.processor.processor_type =='dummy'):
            if message.type.usage == 'incoming':
                message.receive()
            elif message.type.usage == 'outgoing':
                message.send()
            elif message.type.usage == 'internal':
                message.process()
            else:
                raise Warning(_('EDI Message has no type or unknown one! Please modify the message %s') % message.name)
            
            message.state = 'done'
        return True
    
    @api.one
    def receive(self):
        return True
    
    @api.one
    def send(self):
        return True
    
    @api.one
    def process(self):
        return True
    
    #------------------------------------------------------
    # Notification API
    #------------------------------------------------------
    @api.multi
    def set_message_read(self, read, create_missing=True):
        """ Set messages as (un)read. Technically, the notifications related
            to uid are set to (un)read. If for some msg_ids there are missing
            notifications (i.e. due to load more or thread parent fetching),
            they are created.

            :param bool read: set notification as (un)read
            :param bool create_missing: create notifications for missing entries
                (i.e. when acting on displayed messages not notified)

            :return number of message mark as read
        """
        notification_obj = self.env['mail.notification']
        user_pid = self.env['res.users'].sudo().browse(self.env.user.id).partner_id.id
        domain = [('partner_id', '=', user_pid), ('message_id', 'in', self._ids)]
        if not create_missing:
            domain += [('is_read', '=', not read)]
        notif_ids = notification_obj.search(domain)

        # all message have notifications: already set them as (un)read
        if len(notif_ids) == len(self._ids) or not create_missing:
            notif_ids.write({'is_read': read})
            return len(notif_ids)

        # some messages do not have notifications: find which one, create notification, update read status
        notified_msg_ids = [notification.message_id.id for notification in notification_obj.browse(notif_ids)]
        to_create_msg_ids = list(set(self._ids) - set(notified_msg_ids))
        for msg_id in to_create_msg_ids:
            notification_obj.create({'partner_id': user_pid, 'is_read': read, 'message_id': msg_id})
        notif_ids.write({'is_read': read})
        return len(notif_ids)
    
    @api.model
    def _message_read_dict(self, message, parent_id=False):
        """ Return a dict representation of the message. This representation is
            used in the JS client code, to display the messages. Partners and
            attachments related stuff will be done in post-processing in batch.

            :param dict message: mail.message browse record
        """
        # private message: no model, no res_id
        is_private = False
        if not message.model or not message.res_id:
            is_private = True
        

        try:
            if parent_id:
                max_length = 300
            else:
                max_length = 100
            #body_short = html_email_clean(message.body, remove=False, shorten=True, max_length=max_length)

        except Exception:
            body_short = '<p><b>Encoding Error : </b><br/>Unable to convert this message (id: %s).</p>' % message.id
            _logger.exception(Exception)

        return {'id': message.id,
                'type': message.type.id,
                'body': message.name,
                #'body_short': body_short,
                'model': message.model,
                'res_id': message.res_id,
                #'record_name': message.record_name,
                #'subject': message.subject,
                #'date': message.date,
                #'to_read': message.to_read,
                #'parent_id': parent_id,
                #'partner_ids': [],
                #'is_favorite': message.starred,
                'attachment_ids': [],
            }
        
    #------------------------------------------------------
    # Message loading for web interface
    #------------------------------------------------------
    @api.model
    def _message_read_dict_postprocess(self,messages, message_tree):
        """ Post-processing on values given by message_read. This method will
            handle partners in batch to avoid doing numerous queries.

            :param list messages: list of message, as get_dict result
            :param dict message_tree: {[msg.id]: msg browse record}
        """
        res_partner_obj = self.env['res.partner']
        ir_attachment_obj = self.env['ir.attachment']
        pid = self.env['res.users'].sudo().browse(self.env.user.id).partner_id.id

        # 1. Aggregate partners (author_id and partner_ids) and attachments
        partner_ids = set()
        attachment_ids = set()
        for key, message in message_tree.iteritems():
            '''
            if message.author_id:
                partner_ids |= set([message.author_id.id])
            if message.subtype_id and message.notified_partner_ids:  # take notified people of message with a subtype
                partner_ids |= set([partner.id for partner in message.notified_partner_ids])
            elif not message.subtype_id and message.partner_ids:  # take specified people of message without a subtype (log)
                partner_ids |= set([partner.id for partner in message.partner_ids])
            '''
            if message.attachment_ids:
                attachment_ids |= set([attachment.id for attachment in message.attachment_ids])
        # Read partners as SUPERUSER -> display the names like classic m2o even if no access
        partners = res_partner_obj.sudo().browse(list(partner_ids)).name_get()
        partner_tree = dict((partner[0], partner) for partner in partners)

        # 2. Attachments as SUPERUSER, because could receive msg and attachments for doc uid cannot see
        attachments = ir_attachment_obj.sudo().browse(list(attachment_ids)).read(['id', 'datas_fname', 'name', 'file_type_icon'])
        attachments_tree = dict((attachment['id'], {
            'id': attachment['id'],
            'filename': attachment['datas_fname'],
            'name': attachment['name'],
            'file_type_icon': attachment['file_type_icon'],
        }) for attachment in attachments)

        # 3. Update message dictionaries
        for message_dict in messages:
            message_id = message_dict.get('id')
            message = message_tree[message_id]
            '''
            if message.author_id:
                author = partner_tree[message.author_id.id]
            else:
                author = (0, message.email_from)
            partner_ids = []
            if message.subtype_id:
                partner_ids = [partner_tree[partner.id] for partner in message.notified_partner_ids
                                if partner.id in partner_tree]
            else:
                partner_ids = [partner_tree[partner.id] for partner in message.partner_ids
                                if partner.id in partner_tree]
            '''
            attachment_ids = []
            for attachment in message.attachment_ids:
                if attachment.id in attachments_tree:
                    attachment_ids.append(attachments_tree[attachment.id])
            message_dict.update({
                #'is_author': pid == author[0],
                #'author_id': author,
                #'partner_ids': partner_ids,
                'attachment_ids': attachment_ids,
                #'user_pid': pid
                })
        return True
    
    @api.model
    def _message_read_add_expandables(self,messages, message_tree, parent_tree,
            message_unload_ids=[], thread_level=0, domain=[], parent_id=False):
        """ Create expandables for message_read, to load new messages.
            1. get the expandable for new threads
                if display is flat (thread_level == 0):
                    fetch message_ids < min(already displayed ids), because we
                    want a flat display, ordered by id
                else:
                    fetch message_ids that are not childs of already displayed
                    messages
            2. get the expandables for new messages inside threads if display
               is not flat
                for each thread header, search for its childs
                    for each hole in the child list based on message displayed,
                    create an expandable

            :param list messages: list of message structure for the Chatter
                widget to which expandables are added
            :param dict message_tree: dict [id]: browse record of this message
            :param dict parent_tree: dict [parent_id]: [child_ids]
            :param list message_unload_ids: list of message_ids we do not want
                to load
            :return bool: True
        """
        def _get_expandable(domain, message_nb, parent_id, max_limit):
            return {
                'domain': domain,
                'nb_messages': message_nb,
                'type': 'expandable',
                'parent_id': parent_id,
                'max_limit':  max_limit,
            }

        if not messages:
            return True
        message_ids = sorted(message_tree.keys())

        # 1. get the expandable for new threads
        if thread_level == 0:
            exp_domain = domain + [('id', '<', min(message_unload_ids + message_ids))]
        else:
            exp_domain = domain + ['!', ('id', 'child_of', message_unload_ids + parent_tree.keys())]
        more_count = self.search(exp_domain, limit=1)
        if more_count:
            # inside a thread: prepend
            if parent_id:
                messages.insert(0, _get_expandable(exp_domain, -1, parent_id, True))
            # new threads: append
            else:
                messages.append(_get_expandable(exp_domain, -1, parent_id, True))

        # 2. get the expandables for new messages inside threads if display is not flat
        if thread_level == 0:
            return True
        for message_id in message_ids:
            message = message_tree[message_id]

            # generate only for thread header messages (TDE note: parent_id may be False is uid cannot see parent_id, seems ok)
            if message.parent_id:
                continue

            # check there are message for expandable
            child_ids = set([child.id for child in message.child_ids]) - set(message_unload_ids)
            child_ids = sorted(list(child_ids), reverse=True)
            if not child_ids:
                continue

            # make groups of unread messages
            id_min, id_max, nb = max(child_ids), 0, 0
            for child_id in child_ids:
                if not child_id in message_ids:
                    nb += 1
                    if id_min > child_id:
                        id_min = child_id
                    if id_max < child_id:
                        id_max = child_id
                elif nb > 0:
                    exp_domain = [('id', '>=', id_min), ('id', '<=', id_max), ('id', 'child_of', message_id)]
                    idx = [msg.get('id') for msg in messages].index(child_id) + 1
                    # messages.append(_get_expandable(exp_domain, nb, message_id, False))
                    messages.insert(idx, _get_expandable(exp_domain, nb, message_id, False))
                    id_min, id_max, nb = max(child_ids), 0, 0
                else:
                    id_min, id_max, nb = max(child_ids), 0, 0
            if nb > 0:
                exp_domain = [('id', '>=', id_min), ('id', '<=', id_max), ('id', 'child_of', message_id)]
                idx = [msg.get('id') for msg in messages].index(message_id) + 1
                # messages.append(_get_expandable(exp_domain, nb, message_id, id_min))
                messages.insert(idx, _get_expandable(exp_domain, nb, message_id, False))

        return True
            
    @api.multi
    def message_read(self,domain=None, message_unload_ids=None,thread_level=0, parent_id=False, limit=None):
        """ Read messages from mail.message, and get back a list of structured
            messages to be displayed as discussion threads. If IDs is set,
            fetch these records. Otherwise use the domain to fetch messages.
            After having fetch messages, their ancestors will be added to obtain
            well formed threads, if uid has access to them.

            After reading the messages, expandable messages are added in the
            message list (see ``_message_read_add_expandables``). It consists
            in messages holding the 'read more' data: number of messages to
            read, domain to apply.

            :param list ids: optional IDs to fetch
            :param list domain: optional domain for searching ids if ids not set
            :param list message_unload_ids: optional ids we do not want to fetch,
                because i.e. they are already displayed somewhere
            :param int parent_id: context of parent_id
                - if parent_id reached when adding ancestors, stop going further
                  in the ancestor search
                - if set in flat mode, ancestor_id is set to parent_id
            :param int limit: number of messages to fetch, before adding the
                ancestors and expandables
            :return list: list of message structure for the Chatter widget
        """
        assert thread_level in [0, 1], 'message_read() thread_level should be 0 (flat) or 1 (1 level of thread); given %s.' % thread_level
        domain = domain if domain is not None else []
        message_unload_ids = message_unload_ids if message_unload_ids is not None else []
        if message_unload_ids:
            domain += [('id', 'not in', message_unload_ids)]
        limit = limit or self._message_read_limit
        message_tree = {}
        message_list = []
        parent_tree = {}

        # no specific IDS given: fetch messages according to the domain, add their parents if uid has access to
        if self._ids is None:
            ids = self.search(domain, limit=limit)
        else:
            ids = self._ids

        # fetch parent if threaded, sort messages
        for message in self.browse(ids):
            message_id = message.id
            if message_id in message_tree:
                continue
            message_tree[message_id] = message

            # find parent_id
            if thread_level == 0:
                tree_parent_id = parent_id
            else:
                tree_parent_id = message_id
                parent = message
                while parent.parent_id and parent.parent_id.id != parent_id:
                    parent = parent.parent_id
                    tree_parent_id = parent.id
                if not parent.id in message_tree:
                    message_tree[parent.id] = parent
            # newest messages first
            parent_tree.setdefault(tree_parent_id, [])
            if tree_parent_id != message_id:
                parent_tree[tree_parent_id].append(self._message_read_dict(message_tree[message_id], parent_id=tree_parent_id))

        if thread_level:
            for key, message_id_list in parent_tree.iteritems():
                message_id_list.sort(key=lambda item: item['id'])
                message_id_list.insert(0, self._message_read_dict(message_tree[key]))

        # create final ordered message_list based on parent_tree
        parent_list = parent_tree.items()
        parent_list = sorted(parent_list, key=lambda item: max([msg.get('id') for msg in item[1]]) if item[1] else item[0], reverse=True)
        message_list = [message for (key, msg_list) in parent_list for message in msg_list]

        # get the child expandable messages for the tree
        self._message_read_dict_postprocess(message_list, message_tree)
        self._message_read_add_expandables(message_list, message_tree, parent_tree,
            thread_level=thread_level, message_unload_ids=message_unload_ids, domain=domain, parent_id=parent_id)
        return message_list
    
    
class EDIMessageType(models.Model):
    _name='edi.message.type'
    
    name = fields.Char('Name', required=True, index=True,translate=True)
    color = fields.Integer('Color')
    usage = fields.Selection([('incoming', 'Incoming'), ('outgoing', 'Outgoing'), ('internal', 'Internal')], 'Direction of Message', required=True)
    processor = fields.Many2one('edi.processor',string='Processor',required=True)
    
    _sql_constraints=[('usage_processor_unique','UNIQUE(usage,processor)','You can define only use an usage for one processor')]
    
   
    
    
    
    