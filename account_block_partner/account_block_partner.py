# -*- coding: utf-8 -*-
from openerp import models,fields,api
from datetime import datetime
from openerp.tools.translate import _

class purchase_order(models.Model):
    
    _inherit = 'purchase.order'
    
    @api.multi
    def check_customer_block(self):
        res = False

        for order in self:
            for sale in order.sale_ids:
                if sale.partner_id.blocked:
                    return sale.partner_id.blocked
                
        return res
    
    @api.multi
    def check_customer_unblocked(self):
        res = True

        for order in self:
            for sale in order.sale_ids:
                if sale.partner_id.blocked:
                    return not sale.partner_id.blocked
                
        return res
    
    
    @api.multi
    def warn_blocked(self):
        for order in self:
            for sale in order.sale_ids:
                if sale.partner_id.blocked:
                    order.message_post(body=_('Purchase blocked due to customer: %s.') % (sale.partner_id.name or ''),
                subtype="purchase.customer_blocked",type="email")
                    
    @api.multi
    def unblocked(self):
        for order in self.filtered(lambda r:r.is_blocked == True):
            order.account_unblocked = True
            order.message_post(body=_('Purchase unblocked'),
                subtype="purchase.customer_unblocked",type="notification")
            
    @api.one
    def _is_blocked(self):
        self.is_blocked = False

        for sale in self.sale_ids:
            if sale.partner_id.blocked:
                self.is_blocked = sale.partner_id.blocked
                
    @api.multi
    def action_blocked_partners(self):
        mod_obj = self.env['ir.model.data']
        dummy, action_id = tuple(mod_obj.get_object_reference('base', 'action_partner_tree_view1'))
        action = self.env['ir.actions.act_window'].browse(action_id)
        #action = action_obj.read()[0]

        #override the context to get rid of the default filtering on picking type
        #action['context'] = {}
        #choose the view_mode accordingly
        if self.sale_count > 1:
            action['domain'] = "[('id','in',[" + ','.join(map(str, self.sale_ids.mapped('partner_id.id'))) + "])]"
            action['view_mode']="tree"
        else:
            dummy, action_id = tuple(mod_obj.get_object_reference('base', 'action_partner_form'))
            action = self.env['ir.actions.act_window'].browse(action_id)
            #action['views'] = [(res and res[1] or False, 'form')]
            action['res_id'] = self.sale_ids.mapped('partner_id.id')[0] or False
            action['view_mode']= "form"
        return {'name':action.name,
                'view_mode':action.view_mode,
                'view_id':action.view_id.id,
                'view_type':action.view_type,
                'res_model':action.res_model,
                'res_id':action.res_id,
                'type':action.type,
                'target':'self',
                'domain':action.domain,
                'context':self.env.context
                
                }
    
    @api.one
    def _count_blocked_partners(self):
        self.count_blocked_partners = len(self.sale_ids.filtered(lambda r:r.partner_id.blocked).mapped('partner_id'))
                
                    
    is_blocked = fields.Boolean(compute='_is_blocked',string="Is Blocked")
    account_unblocked = fields.Boolean(string="Unblocked (Accounting)", help="The purchase is manually unblocked as it was blocked by accounting (through linked sale orders)")
    
    count_blocked_partners = fields.Integer(compute=_count_blocked_partners,help="Blocked Related Partners")

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    unblock = fields.Boolean('Unblock',help="Use this to unblock this sale only for a blocked customer",track_visibility="onchange")
    partner_blocked = fields.Boolean(related="partner_id.commercial_partner_id.blocked",string="Partner blocked")
    
    @api.multi
    def onchange_partner_id(self, partner):
        res = super(sale_order, self).onchange_partner_id(partner)
        
        if not partner:
            return res
        
        part = self.env['res.partner'].browse(partner)
        
        if part.blocked == True:
            title = _("Customer blocked")
            message = _("Warning: the customer is blocked")
            if 'warning' in res and 'title' in res['warning']:
                title = title + ' & ' + res['warning']['title']
            if 'warning' in res and 'message' in res['warning']:
                message = message + ' & ' + res['warning']['message']
            
            res['warning'] = {
                    'title':  title,
                    'message': message,}
        return res
    
    
    @api.multi
    def unblock_order(self):
        for order in self:
            order.unblock = True
            
    @api.multi
    def reblock_order(self):
        for order in self:
            order.unblock=False
      
    
sale_order()

class stock_picking_type(models.Model):
    _inherit = 'stock.picking.type'
    
    @api.one
    def _get_count_picking_blocked(self):
        domain = [('state', '=', 'blocked'), ('picking_type_id', '=', self.id)]
        count = self.env['stock.picking'].search_count(domain)
        self.count_picking_blocked = count
        
        
    count_picking_blocked = fields.Integer('Number of blocked pickings', compute='_get_count_picking_blocked')
        
stock_picking_type()

class stock_picking(models.Model):
    _inherit = 'stock.picking'
    
    @api.multi
    @api.depends('group_id')
    def _get_sale_id(self):
        for pick in self:
            if pick.group_id:
                pick.sale_id=self.env['sale.order'].search([('procurement_group_id', '=', pick.group_id.id)])
            else:
                pick.sale_id=None

    
    sale_id = fields.Many2one('sale.order',compute='_get_sale_id', store=True)
    
    @api.multi
    @api.depends('move_lines.state','move_lines.picking_id','move_lines.partially_available','move_type','sale_id.unblock')
    @api.v8
    def __state_get(self):
        res = super(stock_picking, self)._state_get(['state'], {})
        for pick in self:
            if pick.id in res:
                state = res[pick.id]
                if pick.picking_type_id and pick.picking_type_id.code == 'outgoing' and pick.partner_id.blocked and not pick.sale_id.unblock and state == 'assigned':
                    state = 'blocked'
                pick.state = state
                
    state = fields.Selection(selection=[
                ('draft', 'Draft'),
                ('cancel', 'Cancelled'),
                ('waiting', 'Waiting Another Operation'),
                ('confirmed', 'Waiting Availability'),
                ('partially_available', 'Partially Available'),
                ('blocked', 'Blocked'),
                ('assigned', 'Ready to Transfer'),
                ('done', 'Transferred')
                ], 
                compute='_state_get', 
                copy=False, 
                store=True,
                string='Status', 
                readonly=True, 
                select=True, 
                track_visibility='onchange',
                help="""
                    * Draft: not confirmed yet and will not be scheduled until confirmed\n
                    * Waiting Another Operation: waiting for another move to proceed before it becomes automatically available (e.g. in Make-To-Order flows)\n
                    * Waiting Availability: still waiting for the availability of products\n
                    * Partially Available: some products are available and reserved\n
                    * Ready to Transfer: products reserved, simply waiting for confirmation.\n
                    * Transferred: has been processed, can't be modified or cancelled anymore\n
                    * Cancelled: has been cancelled, can't be confirmed anymore"""
        )
    
stock_picking()


class res_partner(models.Model):
    _inherit = 'res.partner'
    
    blocked = fields.Boolean('Blocked', help="If it's checked, it's mean that all the deliveries for this client are blocked (manage by account departement)")
    
    block_reason_title = fields.Selection([('unpayed_invoice','Invoice is not payed'),('bad_payed','Bad payer')],'Block reason')
    unpaid_comment = fields.Text('Unpaid comment',  help="The reason why the client is blocked")
    unpaid_history = fields.Text('Unpaid history',  help="History of unpaid")
    unpaid_write_date = fields.Datetime("Unpaid last update date", readonly=True)
    
    @api.one
    def write(self, vals):
        if 'block_reason_title' in vals or 'unpaid_comment' in vals or 'unpaid_history' in vals:
            vals['unpaid_write_date'] = datetime.now()      
        
        #manage users who follow blocked users : 
        # - Subscribe members of group 'Follow blocked partners' to message sub-type mt_partner_payment and mt_partner_block on blocked partner
        # - Un-subscribe members of group 'Follow blocked partners' to message sub-type mt_partner_payment on un-blocked partner
        # - Send message to indicate partner is blocked or un-blocked to all users following mt_partner_block 
        if 'blocked' in vals:
            group_blocked_partners = self.env['res.groups'].search([('name','=','Follow blocked partners')])
            partner_block_subtype_id = self.env['ir.model.data'].xmlid_to_res_id('account_block_partner.mt_partner_block')
            if vals['blocked'] == True:
                text = _('<p><b>%s</b> blocked</p>')%(self.name)
                partner_payment_subtype_id = self.env['ir.model.data'].xmlid_to_res_id('account_block_partner.mt_partner_payment')
                self.message_subscribe_users([u.id for u in group_blocked_partners.users], [partner_block_subtype_id,partner_payment_subtype_id])
                self.message_post(body=text, subtype='account_block_partner.mt_partner_block')
            else:
                text = _('<p><b>%s</b> un-blocked</p>')%(self.name)
                self.message_post(body=text, subtype='account_block_partner.mt_partner_block')
                self.message_unsubscribe_users([u.id for u in group_blocked_partners.users])
                        
        res = super(res_partner, self).write(vals)      
        return res


class account_voucher(models.Model):
    _inherit = 'account.voucher'
    
    @api.multi
    def proforma_voucher(self):
        res = super(account_voucher, self).proforma_voucher()
        text = _('<p><b>%s</b> payment !</p>')%self.partner_id.name
        self.partner_id.message_post(body=text, subtype='account_block_partner.mt_partner_payment')
        return res
        
        
    
account_voucher()
