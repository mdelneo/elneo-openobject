from openerp import models, fields, api

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    @api.multi
    def product_id_change_with_wh(self, pricelist=False, product=False, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, warehouse_id=False):
        
        res = super(sale_order_line, self).product_id_change_with_wh(pricelist, product, qty, uom, qty_uos, uos, name, partner_id, lang, update_tax, date_order, packaging, fiscal_position, flag, warehouse_id)
        
        product = self.env['product.product'].browse(product)
        warehouse = self.env['stock.warehouse'].browse(warehouse_id)
        
        if product:
            current_stock = product.with_context({'location':warehouse.lot_stock_id.id})._product_available()[product.id]
            if current_stock and ('qty_available' in current_stock):
                qty_in_stock = current_stock['qty_available']
            else:
                qty_in_stock = 0
                
            qty_other_wh = {}
            for other_wh in warehouse.resupply_wh_ids:
                qty_other_wh[other_wh] = product.with_context({'location':other_wh.lot_stock_id.id})._product_available()[product.id]['qty_available']
            
            if qty_in_stock <= 0:
                ""
        return res
    
sale_order_line()

class stock_picking(models.Model):
    _inherit = 'stock.picking'
    
stock_picking()

class procurement_rule(models.Model):
    _inherit = 'procurement.rule'
    
    autovalidate_dest_move = fields.Boolean('Auto-validate destination move')

procurement_rule()

class stock_move(models.Model):
    _inherit = 'stock.move'
    
    auto_validate_dest_move = fields.Boolean('Auto validate', related='procurement_id.rule_id.autovalidate_dest_move', help='If this move is "autovalidate", when it became assigned, it is automatically set as done.')
    
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
                move.move_dest_id.action_done()
        return res
    
    
    #reservation will be available when at least one product is available. for delivery order it depends on sale order.
    def _prepare_picking_assign(self, cr, uid, move, context=None):
        res = super(stock_move, self)._prepare_picking_assign(cr, uid, move, context=context)
        if move.picking_type_id and move.picking_type_id.code == 'internal':
            res['move_type'] = 'direct'
        return res
    
    
    #bug correction : include assigned and partially_available state in query
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