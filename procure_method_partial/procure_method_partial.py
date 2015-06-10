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
    
    @api.one
    def _run_move_create(self, procurement, qty, qty_uos):
        vals = procurement._run_move_create(procurement)
        vals['product_uom_qty'] = qty
        vals['product_uos_qty'] = qty_uos
        vals['location_id'] = self.location_src_id
        vals['procure_method'] = self.procure_method
        return vals
    
    rule_id = fields.Many2one('procurement.rule', 'Rule')
    procure_method = fields.Selection([('make_to_stock', 'Take From Stock'), ('make_to_order', 'Create Procurement')], 'Move Supply Method', required=True)
    location_src_id = fields.Many2one('stock.location', 'Source location')
    sequence = fields.Integer(string='Sequence', help="First procure method will be applied first.")
    partner_address_id = fields.Many2one('res.partner', 'Partner address')
    delay = fields.Integer('Delay (days)')
    
procurement_rule_procure_method()

class stock_move(models.Model):
    
    _inherit = 'stock.move'
    
stock_move()


class procurement_order(models.Model):
    _inherit = 'procurement.order'

    @api.model
    def _run(self, procurement):
        if procurement.rule_id and procurement.rule_id.action == 'moves':
            remaining_qty = procurement.product_qty
            for procure_method in procurement.rule_id.procure_methods:
                
                #find remaining quantity for the product in specified location
                qty_in_stock = 0.0
                self._context.update({
                    'states': ['done'],
                    'what': ('in', 'out'),
                    'location':procure_method.location_src_id,
                })
                avail_product_details = procurement.product_id.get_product_available()
                if avail_product_details.values():
                    qty_in_stock = avail_product_details.values()[0]
                
                qty_from_stock = min(qty_in_stock,remaining_qty)
                
                move_dict = procure_method._run_move_create(procurement, qty_from_stock, qty_from_stock)
                self.env['stock.move'].sudo().create(move_dict)
                
                remaining_qty = remaining_qty - qty_from_stock
            return True
        return super(procurement_order, self)._run(procurement)
    
procurement_order