from datetime import datetime
from openerp import models, fields, api, _
from openerp.exceptions import Warning

class StockWarehouse(models.Model):
    _inherit='stock.warehouse'
    
    maint_ret_type_id = fields.Many2one('stock.picking.type',string='Maintenance return type')
    
    
    @api.model
    def _install_maintenance_return_picking_type(self):
        warehouses = self.env['stock.warehouse'].search([])
        
        '''
        Create sequence if no maint_ret_type_id
        '''
        type_id = warehouses.mapped('maint_ret_type_id')
        if not type_id:
            sequence = self.env['ir.sequence'].create({
                                            'name' : 'Maintenance return sequence',
                                            'prefix':'RET_MAINT',
                                            'padding':5,
                                            'number_increment':1,
                                            'number_next_actual':1,
                                            'implementation':'standard'
                                            })
        else:
            sequence = type_id[0].sequence_id
        
        
        for warehouse in warehouses:
            if not warehouse.maint_ret_type_id:
                
                dest_id = warehouse.lot_stock_id
                    
                res = self.env['stock.picking.type'].create({
                                                       'name':'Maintenance Return',
                                                       'sequence_id' : sequence.id,
                                                       'code':'incoming',
                                                       'default_location_src_id':warehouse.wh_output_stock_loc_id.id,
                                                       'default_location_dest_id':warehouse.lot_stock_id.id,
                                                       'warehouse_id':warehouse.id
                                                       })
                warehouse.maint_ret_type_id = res
        return True
    
class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    maint_restocking_user = fields.Many2one('res.users','Technician')
    is_maint_restocking=fields.Boolean("Maintenance restocking")
    
    
class MaintenanceIntervention(models.Model):
    _inherit = 'maintenance.intervention'    
    
    
    @api.one
    def manage_diff_qty(self,diff_qty): #function to override in other modules

        diff_inf = []
        diff_sup = []
        for diff in diff_qty:
            if diff[1] > 0:
                diff_sup.append(diff)
            elif diff[1] < 0:
                diff_inf.append(diff)                                
        
        #manage restocking
        if diff_inf and self.tasks:
            #find previous return pickings
            old_pickings = self.env['stock.picking'].search([('name','=','maint-return : '+self.code),('state','!=','done')])
            if old_pickings:
                old_pickings.unlink()
                
            found=False
            # Looking for products with order lines - if none, stop restocking
            for diff in diff_inf:
                if diff[2]:
                    found=True
                    continue
                    
            if found :
                if not self.warehouse_id.maint_ret_type_id:
                    raise Warning(_('Your warehouse is not well configured. You don t have a picking type for maintenance returns defined for your warehouse.\n\nPlease contact your warehouse administrator'))
                
                picking_restock_id = self.env['stock.picking'].create({
                            'name': 'maint-return : '+self.code,
                            'partner_id':self.partner_id.id,
                            'note': self.partner_id.name, 
                            'origin': self.code,
                            'picking_type_id': self.warehouse_id.maint_ret_type_id.id,
                            'state': 'draft',
                            'move_type': 'direct',
                            'invoice_state': 'none',
                            'company_id': self.sale_order_id.company_id.id,
                            'is_maint_restocking':True,
                            'maint_restocking_user':self.tasks[0].user_id.id, 
                        })
                    
                
                for diff in diff_inf:
                    product = self.env['product.product'].browse(diff[0])
                    now = datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")
                    
                    order_line = None
                    product_uom_id = None
                    product_uos_id = None
                    
                    if diff[2]:
                        order_line = self.env['sale.order.line'].browse(diff[2])
                        product_uom_id = order_line.product_uom.id
                        product_uos_id = order_line.product_uos.id
                    else:
                        continue
                        #Manual products - No sale order line
                        #product = self.pool.get("product.product").browse(cr, uid, diff[0], context=context)
                        #product_uom_id = product.uom_id.id
                        #product_uos_id = product.uos_id.id
                        
                        
                    self.env['stock.move'].create({
                            'picking_id':picking_restock_id.id,
                            'location_id':picking_restock_id.picking_type_id.default_location_src_id.id, 
                            'location_dest_id':picking_restock_id.picking_type_id.default_location_dest_id.id, 
                            'product_id':diff[0], 
                            'product_uom_qty':-diff[1], 
                            'product_uos_qty':-diff[1], 
                            'name': product.name_get()[0][1], 
                            'date':now, 
                            'date_expected':now, 
                            'description':product.name_get()[0][1],
                            'state':'draft', 
                            'note':'Maintenance return', 
                            'company_id':self.sale_order_id.company_id.id, 
                            'product_uom':product_uom_id,
                            'product_uos':product_uos_id
                        })
        
        return True

class StockTransferDetails(models.TransientModel):
    _inherit = 'stock.transfer_details'
    
    @api.one
    def do_detailed_transfer(self):
        res = super(StockTransferDetails, self).do_detailed_transfer()
        
        warehouse = self.env['stock.warehouse'].search([('view_location_id.child_ids','in',self.picking_id.location_dest_id.id)])
        if warehouse.maint_ret_type_id == self.picking_id.picking_type_id:
            '''
            We take the return's backorders and cancel them (If we dont return the whole picking)
            ''' 
            
            backorders = self.env['stock.picking'].search([('backorder_id','=',self.picking_id.id)])
            if backorders:
                backorders.action_cancel()

        return res