# -*- coding: utf-8 -*-
from openerp import models,fields,api,osv
from datetime import datetime
from openerp.tools.translate import _

class purchase_order(models.Model):
    
    _inherit = 'purchase.order'
    
    @api.multi
    def wkf_confirm_order(self):
        alert = False
        for order in self:
            for sale in order.sale_orders:
                if sale.partner_id.blocked or (sale.stop_delivery and sale.block_delivery == 'blocked_client'):
                    alert = True
                    
        if alert:
            view_id = self.env['ir.model.data'].get_object_reference('sale_block_delivery', 'view_purchase_blocked_wizard')
            return {
                    'name':_("Purchase confirm warning"),
                    'view_mode': 'form',
                    'view_type': 'form',
                    'view_id':[view_id[1]],
                    'res_model': 'purchase.blocked.wizard',
                    'type': 'ir.actions.act_window',
                    'nodestroy': True,
                    'target': 'new',
                    'domain': '[]',
                    'context': dict(self._context, active_ids=self._ids)
                    }
        result = super(purchase_order, self).purchase_confirm_elneo()
        return result
    
purchase_order()

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    unblock = fields.Boolean('Unblock')
    
    def onchange_partner_id(self, cr, uid, ids, partner_id, context):
        res = super(sale_order, self).onchange_partner_id(cr, uid, ids, partner_id, context) 
        
        if not partner_id:
            return res
        
        part = self.pool.get('res.partner').browse(cr, uid, partner_id) 
        if part.blocked == True:
            title =  _("Attention: the customer is blocked") 
            message = _("Attention: the customer is blocked") 
            res['warning'] = {
                    'title': title,
                    'message': message,}
        return res
      
    
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
    @api.depends('move_lines.state','move_lines.picking_id','move_lines.partially_available','move_type')
    def _state_get(self):
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
    
    @api.multi
    def write(self, vals):
        if 'block_reason_title' in vals or 'unpaid_comment' in vals or 'unpaid_history' in vals:
            vals['unpaid_write_date'] = datetime.now()      
        
        #manage users who follow blocked users
        if 'blocked' in vals:
            group_blocked_partners = self.env['res.groups'].search([('name','=','Follow blocked partners')])
            for user in group_blocked_partners.users:
                if vals['blocked'] == True:
                    self.env['mail.followers'].create({'res_model':'res.partner', 'res_id':self.id, 'partner_id':user.partner_id.id})
                else:
                    mail_followers = self.env['mail.followers'].search(
                        [('res_model','=','res.partner'), ('res_id','=',self.id), ('partner_id','=',user.partner_id.id)]
                    )
                    for mail_follower in mail_followers:
                        mail_follower.unlink()
                        
        res = super(res_partner, self).write(vals)      
        return res
    
res_partner()