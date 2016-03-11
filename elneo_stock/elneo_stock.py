from openerp import models, fields, api
from openerp.exceptions import Warning
from openerp.tools.translate import _
import time
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import logging
_logger = logging.getLogger(__name__)

class stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'
    
    @api.multi
    def do_detailed_transfer(self):
        res = super(stock_transfer_details,self).do_detailed_transfer()
        return self.picking_id.do_print_picking()


class StockMoveOperationLink(models.Model):
    _inherit = 'stock.move.operation.link'
    
    move_id = fields.Many2one(index=True)
    reserved_quant_id = fields.Many2one(index=True) 
    
class StockWarehouse(models.Model):
    _inherit='stock.warehouse'
    
    default_user_ids = fields.One2many('res.users','default_warehouse_id',string='Users Default Warehouse',help='Users that have defined this warehouse as default')

class stock_warehouse_orderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'
    stocked_for_customer = fields.Boolean('Stocked for customer')

class procurement_order(models.Model):  
    _inherit = 'procurement.order'
    
    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        new_procurement = super(procurement_order, self).create(vals)
        if self._context.get('from_scheduler'):
            new_procurement.run()
            new_procurement.check()
        return new_procurement
    
    @api.model
    def _procure_orderpoint_confirm(self, use_new_cursor=False, company_id = False):
        return super(procurement_order, self.with_context(make_po=False))._procure_orderpoint_confirm(use_new_cursor,company_id)
    
    @api.model
    def run_procurements(self):
        procurements_confirmed = self.sudo().search([('state', '=', 'confirmed')])
        _logger.warn('Running %s procurements', str(len(procurements_confirmed)))        
        procurements_confirmed.with_context(from_scheduler=True).run()
        return {}
        
    @api.model
    def check_procurements(self):
        procurements_running = self.sudo().search([('state', '=', 'running')])
        _logger.warn('Check %s procurements', str(len(procurements_running)))
        procurements_running.with_context(from_scheduler=True).check()
        return {}
    


    
class stock_picking(models.Model):
    _inherit = 'stock.picking'
    
    picking_type_id = fields.Many2one(track_visibility="onchange")
    group_id = fields.Many2one(index=True)
    section_id = fields.Many2one('crm.case.section', string="Sales team", compute="_get_section_id", store=True)
    reservation_name = fields.Char('Linked reservation', compute='_get_reservation_name')
    
    
    @api.model
    def check_availability(self):
        self._cr.execute('''select distinct p.id 
from stock_picking p 
left join stock_move m on m.picking_id = p.id 
where 
p.state in ('waiting','confirmed','partially_available') 
and m.state not in ('draft', 'cancel', 'done')
group by p.id
having
count(m.id) > 0''')
        res = self._cr.fetchall()
        picking_ids = [r[0] for r in res]
        pickings = self.browse(picking_ids)
        _logger.warn('Check %s pickings', str(len(pickings)))
        pickings.with_context(from_scheduler=True).recheck_availability()
        return {}
    
    @api.one
    def _get_reservation_name(self):
        if self.group_id:
            int_pickings = self.env['stock.picking'].search([('group_id','=',self.group_id.id), ('picking_type_id.code','=','internal')])
            self.reservation_name = ','.join([int_picking.name for int_picking in int_pickings])
    
    @api.one
    def _get_section_id(self):
        self.section_id = self.create_uid.default_section_id
    
    @api.cr_uid_ids_context
    def do_enter_transfer_details(self, cr, uid, picking, context=None):
        pick = self.browse(cr, uid, picking, context)
        if pick.picking_type_id and pick.picking_type_id.code == 'internal':
            raise Warning(_('You must validate a reservation line by line'))
        
        return super(stock_picking,self).do_enter_transfer_details(cr, uid, picking, context)
    
    @api.cr_uid_ids_context
    def do_transfer(self, cr, uid, picking_ids, context=None):
        res = super(stock_picking,self).do_transfer(cr, uid, picking_ids, context)
        for pick in self.browse(cr, uid, picking_ids, context):
            pick.action_sync()
        return res
    
    @api.returns('self')
    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        #if my_dpt : display picking of sale teams of current user. If user is not linked to a sale team, display all picks 
        section_ids = self.pool.get('crm.case.section').search(cr, user, [('member_ids','in',user)], context=context)
        if context.get('my_dpt_stock',False) and section_ids:
            args.append(('section_id','in',section_ids))
        res = super(stock_picking, self).search(cr, user, args, offset=offset, limit=limit, order=order, context=context, count=count)
        return res
    
    
    
stock_picking()

class res_users(models.Model):
    _inherit = 'res.users'
    section_ids = fields.Many2many('crm.case.section', 'sale_member_rel', 'member_id', 'section_id', 'Sale teams')
    

class stock_picking_type(models.Model):
    _inherit = 'stock.picking.type'
    
    def _get_picking_count(self, cr, uid, ids, field_names, arg, context=None):
        obj = self.pool.get('stock.picking')
        domains = {
            'count_picking_draft': [('state', '=', 'draft')],
            'count_picking_waiting': [('state', 'in', ['confirmed','waiting'])],
            'count_picking_ready': [('state', 'in', ('assigned', 'partially_available'))],
            'count_picking': [('state', 'in', ('assigned', 'waiting', 'confirmed', 'partially_available'))],
            'count_picking_late': [('min_date', '<', time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)), ('state', 'in', ('assigned', 'waiting', 'confirmed', 'partially_available'))],
            'count_picking_backorders': [('backorder_id', '!=', False), ('state', 'in', ('confirmed', 'assigned', 'waiting', 'partially_available'))],
        }
        result = {}
        for field in domains:
            data = obj.read_group(cr, uid, domains[field] +
                [('state', 'not in', ('done', 'cancel')), ('picking_type_id', 'in', ids)],
                ['picking_type_id'], ['picking_type_id'], context=context)
            count = dict(map(lambda x: (x['picking_type_id'] and x['picking_type_id'][0], x['picking_type_id_count']), data))
            for tid in ids:
                result.setdefault(tid, {})[field] = count.get(tid, 0)
        for tid in ids:
            if result[tid]['count_picking']:
                result[tid]['rate_picking_late'] = result[tid]['count_picking_late'] * 100 / result[tid]['count_picking']
                result[tid]['rate_picking_backorders'] = result[tid]['count_picking_backorders'] * 100 / result[tid]['count_picking']
            else:
                result[tid]['rate_picking_late'] = 0
                result[tid]['rate_picking_backorders'] = 0
        return result
    
stock_picking_type()
    

class procurement_rule(models.Model):
    _inherit = 'procurement.rule'
    
    autovalidate_dest_move = fields.Boolean('Auto-validate destination move')

procurement_rule()

class stock_move(models.Model):
    _inherit = 'stock.move'
    
    picking_type_code = fields.Selection(related='picking_id.picking_type_id.code')
    auto_validate_dest_move = fields.Boolean('Auto validate', related='procurement_id.rule_id.autovalidate_dest_move', help='If this move is "autovalidate", when it became assigned, it is automatically set as done.')
    procurement_id = fields.Many2one('procurement.order',index=True)
    split_from = fields.Many2one(index=True)
    route_ids=fields.Many2many(auto_join=True)
    product_id=fields.Many2one(auto_join=True)
    puchased = fields.Boolean('Purchased', compute='_purchased')
    aisle = fields.Char('Aisle', compute='_aisle')
    
    @api.multi
    def _aisle(self):
        for m in self:
            if m.product_id and m.product_id.warehouse_detail and m.picking_id and m.picking_id.picking_type_id and m.picking_id.picking_type_id.warehouse_id:
                for detail in m.product_id.warehouse_detail:
                    if detail.warehouse_id.id == m.picking_id.picking_type_id.warehouse_id.id:
                        m.aisle = detail.aisle
                        break;
                    
    
    @api.multi
    def _purchased(self):
        def has_purchase(m):
            if m.purchase_line_id:
                return True
            else:
                #find parent
                parent_moves = self.search([('move_dest_id','=',m.id)])
                if not parent_moves:
                    return False
                for parent_move in parent_moves:
                    if has_purchase(parent_move):
                        return True
            return False
                    
        for move in self:
            #find if a move linked to this move has purchase_line_id
            move.purchased = has_purchase(move)
    
    @api.model
    def _prepare_procurement_from_move(self, move):
        res = super(stock_move,self)._prepare_procurement_from_move(move)
        res['origin'] = move.group_id and move.group_id.name or ''
        if move.product_id:
            res['name'] = move.product_id.name_get()[0][1]
        if move.procurement_id and move.procurement_id.sale_line_id:
            res['sale_line_id'] = move.procurement_id.sale_line_id.id
        return res
    
    @api.multi
    def action_partial_move(self):
        partial_id = self.env["transfert.move.wizard"].create({})
        return {
            'name':_("Products to Process"),
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'transfert.move.wizard',
            'res_id': partial_id.id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': self._context
        }
  
    @api.multi
    def write(self, vals):
        if ('product_uom_qty' in vals):
            self.notify_picking(vals['product_uom_qty'])
        res = super(stock_move,self).write(vals) 
        if ('state' in vals) or ('picking_id' in vals):
            self.state_change()
            
        
        return res
    
    @api.multi
    def notify_picking(self,new_val):
        message = ''
        for move in self:
            if move.product_uom_qty != new_val:
                name = move.name
                message += _('The quantity for the move %s has changed : %s -> %s <br/>') % (name, str(move.product_uom_qty),str(new_val))
                
        if message != '':
            move.picking_id.message_post(body=message)
    
    @api.multi
    def state_change(self):
        for move in self:
            if move.picking_id:
                move.picking_id.action_sync()
    
    @api.multi
    def action_assign(self):
        for move in self:
            previous_moves = self.search([('move_dest_id','=',move.id)])
            all_previous_move_done = False
            if previous_moves:
                all_previous_move_done = True
                for previous_move in previous_moves:
                    if previous_move.state != 'done':
                        all_previous_move_done = False
                        break;
            if all_previous_move_done:
                move.force_assign()
            else:
                super(stock_move, move).action_assign()
        
    
    #check availability automatically
    @api.multi
    def action_confirm(self):
        res = super(stock_move, self).action_confirm()
        pickings = set()
        for move in self:
            pickings.add(move.picking_id)
        for picking in pickings:
            picking.action_assign()
        return res
    
    @api.multi
    def action_done(self):
        #when a move is done, if it's flagged as "autovalidate_dest_move", call action_done on dest_move        
        res = super(stock_move, self).action_done()
        for move in self:
            if move.auto_validate_dest_move and move.move_dest_id:
                if move.move_dest_id.product_uom_qty != move.product_uom_qty:
                    rest = move.move_dest_id.product_uom_qty - move.product_uom_qty
                    if rest > 0:
                        move.move_dest_id.split(rest)
                move.move_dest_id.action_done()
        return res
    
    
    #reservation will be available when at least one product is available. for delivery order it depends on sale order.
    def _prepare_picking_assign(self, cr, uid, move, context=None):
        res = super(stock_move, self)._prepare_picking_assign(cr, uid, move, context=context)
        if move.picking_type_id and move.picking_type_id.code == 'internal':
            res['move_type'] = 'direct'
        return res
    
    
    #include assigned and partially_available state in query
    @api.cr_uid_ids_context
    def _picking_assign(self, cr, uid, move_ids, procurement_group, location_from, location_to, context=None):
        """Assign a picking on the given move_ids, which is a list of move supposed to share the same procurement_group, location_from and location_to
        (and company). Those attributes are also given as parameters.
        """
        pick_obj = self.pool.get("stock.picking")
        # Use a SQL query as doing with the ORM will split it in different queries with id IN (,,)
        # In the next version, the locations on the picking should be stored again.
        query = """
            SELECT stock_picking.id FROM stock_picking, stock_move
            WHERE
                stock_picking.state in ('draft', 'confirmed', 'waiting', 'assigned','partially_available') AND
                stock_move.picking_id = stock_picking.id AND
                stock_move.location_id = %s AND
                stock_move.location_dest_id = %s AND
        """
        params = (location_from, location_to)
        if not procurement_group:
            query += "stock_picking.group_id IS NULL LIMIT 1"
        else:
            query += "stock_picking.group_id = %s LIMIT 1"
            params += (procurement_group,)
        cr.execute(query, params)
        [pick] = cr.fetchone() or [None]
        if not pick:
            move = self.browse(cr, uid, move_ids, context=context)[0]
            values = self._prepare_picking_assign(cr, uid, move, context=context)
            pick = pick_obj.create(cr, uid, values, context=context)
        return self.write(cr, uid, move_ids, {'picking_id': pick}, context=context)
    
    
stock_move()

class product_template(models.Model):
    _inherit = 'product.template'

    #Update default product route to add Make to order
    def _get_buy_route(self):
        res=[]
        res = super(product_template,self)._get_buy_route()
        
        buy_route = self.env['ir.model.data'].xmlid_to_res_id('stock.route_warehouse0_mto')
        if buy_route and buy_route not in res:
            res.append(buy_route)
        

        return res
        
   
    route_ids = fields.Many2many('stock.location.route', 'stock_route_product', 'product_id', 'route_id', 'Routes', domain="[('product_selectable', '=', True)]",default=_get_buy_route,
                                    help="Depending on the modules installed, this will allow you to define the route of the product: whether it will be bought, manufactured, MTO/MTS,...")
    
product_template()
