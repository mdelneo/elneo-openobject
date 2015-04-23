from openerp import models, fields, api


class purchase_order(models.Model):
    
    _inherit='purchase.order'
    
    def _get_sale_orders(self):
       
        self.env.cr.execute('''select distinct purchase_order.id, sale_order.id
                                from sale_order 
                                left join sale_order_line
                                    left join procurement_order
                                        left join stock_move
                                            left join procurement_order po2
                                            left join purchase_order_line
                                                left join purchase_order on purchase_order_line.order_id = purchase_order.id
                                            on po2.purchase_line_id = purchase_order_line.id
                                            on stock_move.id = po2.move_dest_id
                                        on stock_move.procurement_id = procurement_order.id
                                    on procurement_order.sale_line_id = sale_order_line.id
                                on sale_order_line.order_id = sale_order.id
                                where sale_order.state != 'cancel' and purchase_order.id in %s''',(tuple(self.mapped('id')),))
        res = self.env.cr.fetchall()
        
        # IF NO STOCK MOVE, MAYBE A DROPSHIPPING (PROCUREMENT IS THE SAME FOR SALE AND PURCHASE)
        if len(res) == 0:
            self.env.cr.execute('''select distinct purchase_order.id, sale_order.id
                                    from sale_order 
                                    left join sale_order_line
                                        left join procurement_order
                                            left join purchase_order_line
                                            left join purchase_order on purchase_order_line.order_id = purchase_order.id
                                            on procurement_order.purchase_line_id = purchase_order_line.id 
                                        on procurement_order.sale_line_id = sale_order_line.id
                                    on sale_order_line.order_id = sale_order.id
                                    where sale_order.state != 'cancel' and purchase_order.id in %s''',(tuple(self.mapped('id')),))
            res = self.env.cr.fetchall()
        
        # No procurement and no drop shipping, use stock_move
        if len(res) == 0 :
            self.env.cr.execute('''select distinct po.id, so.id
                                    from purchase_order po
                                        left join purchase_order_line pol
                                            left join stock_move sm
                                                left join stock_move sm2
                                                    left join sale_order_line sol
                                                        left join sale_order so on sol.order_id = so.id
                                                    on sm2.sale_line_id = sol.id
                                                on sm.move_dest_id = sm2.id
                                            on pol.id = sm.purchase_line_id
                                        on po.id = pol.order_id
                                    where po.id in %s''',(tuple(self.mapped('id')),))
        
            res = self.env.cr.fetchall()
   
        orders=[]
        for (purchase_id, sale_id) in res:
            orders.append(sale_id)
            
        self.sale_orders=orders
        
            
    
    @api.depends('sale_orders')
    def _count_all(self):
        
        self.sale_count=len(self.sale_orders)
    
    sale_orders = fields.Many2many(comodel_name='sale.order',compute=_get_sale_orders,string='Sale Orders',method=True)
    sale_count = fields.Integer(compute=_count_all, method=True)
    
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
            action['domain'] = "[('id','in',[" + ','.join(map(str, self.sale_orders.mapped('id'))) + "])]"
        else:
            res = mod_obj.get_object_reference('sale', 'view_order_form')
            action['views'] = [(res and res[1] or False, 'form')]
            action['res_id'] = self.sale_orders.mapped('id')[0] or False
        return action
    
purchase_order()