from openerp import models, fields, api
from pygments.lexer import _inherit


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
    def force_assign(self):
        #when a move is assigned, if it's an autovalidate move, end it        
        res = super(stock_move, self).force_assign()
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