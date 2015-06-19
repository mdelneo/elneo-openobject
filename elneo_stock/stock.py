from openerp import models, fields, api

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    #to re-write when framework method will be up to date with new API
    #@api.onchange('product_id')    
    @api.multi
    def product_id_change(self, pricelist=False, product=False, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False):
        '''res = super(sale_order_line, self).product_id_change(self.order_id.pricelist_id, self.product_id, self.product_uom_qty, self.product_uom, self.product_uos_qty, self.product_uos, self.name, 
           self.order_id.partner_id, False, True, self.order_id.date_order, False, self.order_id.fiscal_position, False)'''
        
        res = super(sale_order_line, self).product_id_change(pricelist, product, qty, uom, qty_uos, uos, name, partner_id, lang, update_tax, date_order, packaging, fiscal_position, flag)
        
        product = self.env['product.product'].browse(product)
        
        if product:
            current_stock = product.with_context({'location':self.order_id.warehouse_id.lot_stock_id.id})._product_available()[product.id]
            if current_stock and ('qty_available' in current_stock):
                qty_in_stock = current_stock['qty_available']
            else:
                qty_in_stock = 0
                
            qty_other_wh = {}
            for other_wh in self.order_id.warehouse_id.resupply_wh_ids:
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
    
    @api.multi
    def action_done(self):
        #when a move is done, if it's flagged as "autovalidate_dest_move", call action_done on dest_move        
        res = super(stock_move, self).action_done()
        for move in self:
            if move.auto_validate_dest_move and move.move_dest_id:
                move.move_dest_id.action_done()
        return res
    
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