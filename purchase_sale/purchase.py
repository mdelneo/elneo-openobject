from openerp import models, fields, api

class purchase_order(models.Model):
    _inherit='purchase.order'
   
    @api.multi
    def copy(self, default=None):
        if not default:
            default = {}
        default['sale_ids'] = None
        return super(purchase_order, self).copy(default)
    
    @api.depends('sale_ids')
    def _count_all(self):
        self.sale_count=len(self.sale_ids)
        
    @api.multi
    def view_sale(self):
        '''
        This function returns an action that display existing sale orders of given purchase order ids.
        It load the tree or the form according to the number of sale orders
        '''

        mod_obj = self.env['ir.model.data']
        dummy, action_id = tuple(mod_obj.get_object_reference('sale', 'action_orders'))
        action_obj = self.env['ir.actions.act_window'].browse(action_id)
        action = action_obj.read()[0]

        #override the context to get rid of the default filtering on picking type
        action['context'] = {}
        #choose the view_mode accordingly
        if self.sale_count > 1:
            action['domain'] = "[('id','in',[" + ','.join(map(str, self.sale_ids.mapped('id'))) + "])]"
        else:
            res = mod_obj.get_object_reference('sale', 'view_order_form')
            action['views'] = [(res and res[1] or False, 'form')]
            action['res_id'] = self.sale_ids.mapped('id')[0] or False
        return action

    sale_ids = fields.Many2many('sale.order', 'purchase_sale_rel', 'purchase_id', 'sale_id', 'Sales')
    sale_count = fields.Integer(compute=_count_all)


class purchase_order_line(models.Model):
    _inherit='purchase.order.line'
    
    sale_line_ids = fields.Many2many('sale.order.line', 'purchase_line_sale_line_rel', 'purchase_line_id', 'sale_line_id', 'Sale lines')
    
    @api.multi
    def copy(self, default=None):
        if not default:
            default = {}
        default['sale_line_ids'] = None
        return super(purchase_order_line, self).copy(default)
    

class procurement_order(models.Model):
    
    _inherit = 'procurement.order'
    
    @api.multi
    def make_po(self):
        res = super(procurement_order,self).make_po()
        #link sales with purchase in accordance with procurement group
        for procurement in self:
            if procurement.sale_line_id and procurement.purchase_line_id:
                procurement.sale_line_id.write({'purchase_line_ids':[(4,procurement.purchase_line_id.id)]})
                procurement.sale_line_id.order_id.write({'purchase_ids':[(4,procurement.purchase_line_id.order_id.id)]})
        return res
    
class sale_order(models.Model):
    _inherit='sale.order'
    
    @api.multi
    def copy(self, default=None):
        if not default:
            default = {}
        default['purchase_ids'] = None
        return super(sale_order, self).copy(default)
    
    @api.depends('purchase_ids')
    @api.multi
    def _count_all(self):
        for sale in self:
            sale.purchase_count=len(sale.purchase_ids)
            
        
    @api.multi
    def view_purchase(self):
        '''
        This function returns an action that display existing purchase orders of given purchase order ids.
        It load the tree or the form according to the number of purchase orders
        '''
        
        mod_obj = self.env['ir.model.data']
        dummy, action_id = tuple(mod_obj.get_object_reference('purchase', 'purchase_form_action'))
        action_obj = self.env['ir.actions.act_window'].browse(action_id)
        action = action_obj.read()[0]
        

        #override the context to get rid of the default filtering on picking type
        action['context'] = {}
        #choose the view_mode accordingly
        if self.purchase_count > 1:
            action['domain'] = "[('id','in',[" + ','.join(map(str, self.purchase_ids.mapped('id'))) + "])]"
        else:
            res = mod_obj.get_object_reference('purchase', 'purchase_order_form')
            action['views'] = [(res and res[1] or False, 'form')]
            action['res_id'] = self.purchase_ids.mapped('id')[0] or False
        return action

    purchase_count = fields.Integer(compute=_count_all)
    purchase_ids = fields.Many2many('purchase.order', 'purchase_sale_rel', 'sale_id', 'purchase_id', 'Purchases')