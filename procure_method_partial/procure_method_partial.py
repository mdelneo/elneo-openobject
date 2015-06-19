from openerp import models, fields, api
from openerp.tools.translate import _
from datetime import datetime
from dateutil import relativedelta

class procurement_rule(models.Model):
    
    _inherit = 'procurement.rule'
    
    @api.model
    def _get_action(self):
        result = super(procurement_rule, self)._get_action()
        return result + [('moves', _('Move from different locations'))]
    
    procure_methods = fields.One2many('procurement.rule.procure.method', 'rule_id', string='Procure methods')
    
procurement_rule()


class procurement_rule_procure_method(models.Model):
    _name = 'procurement.rule.procure.method'
    _order = 'sequence'
    
    @api.model
    def _run_move_create(self, procurement, qty, qty_uos):
        vals = procurement._run_move_create(procurement)
        vals['product_uom_qty'] = qty
        vals['product_uos_qty'] = qty_uos
        vals['location_id'] = self.location_src_id.id
        vals['procure_method'] = self.procure_method
        if self.sub_route_id:
            vals['route_ids'] = [(4,self.sub_route_id.id)]
        return vals
    
    rule_id = fields.Many2one('procurement.rule', 'Rule')
    procure_method = fields.Selection([('make_to_stock', 'Take From Stock'), ('make_to_order', 'Create Procurement')], 'Move Supply Method', required=True)
    location_src_id = fields.Many2one('stock.location', 'Source location')
    sequence = fields.Integer(string='Sequence', help="First procure method will be applied first.")
    partner_address_id = fields.Many2one('res.partner', 'Partner address')
    delay = fields.Integer('Delay (days)')
    sub_route_id = fields.Many2one('stock.location.route', 'Sub-route')
    sub_route_quantity_check_location_id = fields.Many2one('stock.location', 'Location for quantity check')
    
procurement_rule_procure_method()

class stock_move(models.Model):
    
    _inherit = 'stock.move'
    
stock_move()


class procurement_order(models.Model):
    _inherit = 'procurement.order'
    
    def use_procure_method(self, procurement, procure_method, remaining_qty):
        return remaining_qty > 0

    @api.model
    def _run(self, procurement):
        if procurement.rule_id and procurement.rule_id.action == 'moves':
            remaining_qty = procurement.product_qty
            for procure_method in procurement.rule_id.procure_methods:
                if self.use_procure_method(procurement, procure_method, remaining_qty):
                    #find remaining quantity for the product in specified location
                    if procure_method.procure_method == 'make_to_stock':
                        qty_in_stock = 0.0
                        qty_in_stock = procurement.product_id.with_context({'location':procure_method.location_src_id.id})._product_available()[procurement.product_id.id]['virtual_available']
                        move_qty = min(qty_in_stock,remaining_qty)
                    elif procure_method.procure_method == 'make_to_order':
                        if procure_method.sub_route_quantity_check_location_id:
                            qty_in_stock = 0.0
                            qty_in_stock = procurement.product_id.with_context({'location':procure_method.sub_route_quantity_check_location_id.id})._product_available()[procurement.product_id.id]['virtual_available']
                            move_qty = min(qty_in_stock,remaining_qty)
                        else:
                            move_qty = remaining_qty
                        
                    if move_qty <= 0:
                        continue
                        
                    move_dict = procure_method._run_move_create(procurement, move_qty, move_qty)
                    move_id = self.env['stock.move'].sudo().create(move_dict)
                    remaining_qty = remaining_qty - move_qty
            return True
        return super(procurement_order, self)._run(procurement)
    
    @api.multi
    def run(self):
        res = super(procurement_order, self).run()
        move_to_confirm = []
        for procurement in self:
            if procurement.state == "running" and procurement.rule_id and procurement.rule_id.action == "moves":
                move_to_confirm += [m for m in procurement.move_ids if m.state == 'draft']
        for m in move_to_confirm:
            m.action_confirm()
        return res
    
procurement_order