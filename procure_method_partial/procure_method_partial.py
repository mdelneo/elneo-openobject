from openerp import models, fields, api
from openerp.tools.translate import _
from datetime import datetime
from dateutil import relativedelta


class sale_order(models.Model):
    _inherit = 'sale.order'
    
    @api.multi
    def action_wait(self):
        for order_line in self.order_line:
            order_line.procurement_path_backup = None
            order_line.procurement_path_backup = order_line.procurement_path
        return super(sale_order, self).action_wait()
    
    @api.multi
    def action_cancel(self):
        for order_line in self.order_line:
            order_line.procurement_path_backup = 'cancel'
        return super(sale_order, self).action_cancel()
    
sale_order()

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    

    def copy_data(self, *args, **kwargs):
        data = super(sale_order_line, self).copy_data(*args, **kwargs)
        if data and data.get('procurement_path_backup'):
            data['procurement_path_backup'] = None
        return data

    
    @api.one
    @api.onchange('route_id','order_id.warehouse_id')
    def get_procurement_path(self):
        if self.procurement_path_backup:
            self.procurement_path = self.procurement_path_backup
        else:
            #find if other lines with same rule and same product exists
            #for the moment self.order_id.order_line return a table with only current_line (self). When the framework works, we can uncomment following lines to test 
            #the goal is to compute procurement path in accordance with quantity of other lines with the same product
            '''
            other_line_qty = 0
            for line in self.order_id.order_line:
                self_ok = False
                if line == self:
                    self_ok = True #don't consider lines after current line.
                if self_ok and line != self and line.product_id and self.product_id and line.product_id.id == self.product_id.id and line.route_id and self.route_id and line.route_id.id == self.route_id.id:
                    other_line_qty = other_line_qty+line.product_uom_qty
            '''
            rule = self.env['procurement.rule'].search([('route_id','=',self.route_id.id),('location_id','=',self.order_id.warehouse_id.wh_output_stock_loc_id.id)])
            if rule:
                #self.procurement_path = rule.get_path(self.product_id, self.product_uom_qty, other_line_qty)
                self.procurement_path = rule.get_path(self.product_id, self.product_uom_qty)
                
    
    procurement_path = fields.Char('Procurement path', compute='get_procurement_path')
    procurement_path_backup = fields.Char('Procurement path (backup)')
    
sale_order_line()

class procurement_rule(models.Model):
    
    _inherit = 'procurement.rule'
    
    @api.model
    def _get_action(self):
        result = super(procurement_rule, self)._get_action()
        return result + [('moves', _('Move from different locations'))]
    
    procure_methods = fields.One2many('procurement.rule.procure.method', 'rule_id', string='Procure methods')
    
    #def get_path(self, product, quantity,other_line_qty):
    def get_path(self, product, quantity):
        remaining_qty = quantity
        path = ''
        
        for procure_method in self.procure_methods:
            purchase = False
            if procure_method.procure_method == 'make_to_stock':
                qty_in_stock = product.with_context({'location':procure_method.location_src_id.id})._product_available()[product.id]['virtual_available']
            elif procure_method.procure_method == 'make_to_order' and procure_method.sub_route_quantity_check_location_id:
                qty_in_stock = product.with_context({'location':procure_method.sub_route_quantity_check_location_id.id})._product_available()[product.id]['virtual_available']
            else:
                purchase = True
            
            #if remaining_qty > 0 and self.env['procurement.order'].use_procure_method(product, procure_method, remaining_qty+other_line_qty, qty_in_stock):
            if remaining_qty > 0 and self.env['procurement.order'].use_procure_method(product, procure_method, remaining_qty, qty_in_stock):
                if purchase: 
                    move_qty = remaining_qty
                else:
                    move_qty = min(qty_in_stock,remaining_qty)
                    
                if move_qty <= 0:
                    continue
                
                remaining_qty = remaining_qty - move_qty
            
                procure_method_name = procure_method.name or ''
                
                path = path+' - '+procure_method_name+' ('+str(move_qty)+')'
        
        return path[3:]
    
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
    
    name = fields.Char('Name', size=255)
    rule_id = fields.Many2one('procurement.rule', 'Rule')
    procure_method = fields.Selection([('make_to_stock', 'Take From Stock'), ('make_to_order', 'Create Procurement')], 'Move Supply Method', required=True)
    location_src_id = fields.Many2one('stock.location', 'Source location')
    sequence = fields.Integer(string='Sequence', help="First procure method will be applied first.")
    partner_address_id = fields.Many2one('res.partner', 'Partner address')
    delay = fields.Integer('Delay (days)')
    sub_route_id = fields.Many2one('stock.location.route', 'Sub-route')
    sub_route_quantity_check_location_id = fields.Many2one('stock.location', 'Location for quantity check')
    warehouse_src_id = fields.Many2one('stock.warehouse', 'Source warehouse')
    use_if_enough_stock = fields.Boolean('Use if enough stock', help='If there is enough stock in location, whatever the other conditions, the procure method will be used')
    
procurement_rule_procure_method()

class stock_move(models.Model):
    
    _inherit = 'stock.move'
    
stock_move()


class procurement_order(models.Model):
    _inherit = 'procurement.order'
    
    def use_procure_method(self, product, procure_method, requested_quantity, qty_in_stock):
        if procure_method.use_if_enough_stock and qty_in_stock > requested_quantity:
            return True

    @api.model
    def _run(self, procurement):
        if procurement.rule_id and procurement.rule_id.action == 'moves':
            remaining_qty = procurement.product_qty
            for procure_method in procurement.rule_id.procure_methods:
                #find remaining quantity for the product in specified location
                purchase = False
                if procure_method.procure_method == 'make_to_stock':
                    qty_in_stock = procurement.product_id.with_context({'location':procure_method.location_src_id.id})._product_available()[procurement.product_id.id]['virtual_available']
                elif procure_method.procure_method == 'make_to_order' and procure_method.sub_route_quantity_check_location_id:
                    qty_in_stock = procurement.product_id.with_context({'location':procure_method.sub_route_quantity_check_location_id.id})._product_available()[procurement.product_id.id]['virtual_available']
                else:
                    purchase = True
                
                if remaining_qty > 0 and self.use_procure_method(procurement.product_id, procure_method, remaining_qty, qty_in_stock):
                    if purchase: 
                        move_qty = remaining_qty
                    else:
                        move_qty = min(qty_in_stock,remaining_qty)
                        
                    if move_qty <= 0:
                        continue
                        
                    move_dict = procure_method._run_move_create(procurement, move_qty, move_qty)
                    move_id = self.env['stock.move'].sudo().create(move_dict)
                    remaining_qty = remaining_qty - move_qty
            return True
        return super(procurement_order, self)._run(procurement)
    
    @api.multi
    def run(self, autocommit=False):
        res = super(procurement_order, self).run(autocommit)
        move_to_confirm = []
        for procurement in self:
            if procurement.state == "running" and procurement.rule_id and procurement.rule_id.action == "moves":
                move_to_confirm += [m for m in procurement.move_ids if m.state == 'draft']
        for m in move_to_confirm:
            m.action_confirm()
        return res
    
procurement_order