# -*- coding: utf-8 -*-
##############################################################################
#
#    Elneo
#    Copyright (C) 2011-2015 Elneo (Technofluid SA) (<http://www.elneo.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models,fields,api, _

from datetime import timedelta,datetime

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    maintenance_product = fields.Boolean("Maintenance product", help="A maintenance product can't be delivered without creating an associated maintenance element.")
    serialnumber_required = fields.Boolean("Serial number required")
    

class MaintenanceInterventionProduct(models.Model):
    _inherit = 'maintenance.intervention.product'
    
    serial_number = fields.Char(size=255, string="Serial number")
    
    
class MaintenanceIntervention(models.Model):
    _inherit = 'maintenance.intervention' 

    @api.multi
    def action_done(self):
        #check if serial number filled and create maintenance element if it's necessary
        for intervention in self:
            for intervention_product in intervention.intervention_products:
                if intervention_product.serial_number and intervention_product.serial_number.count(';')+1 == intervention_product.sale_order_line_id.product_uom_qty:
                    self.env['maintenance.element'].create_default(intervention_product.serial_number, intervention_product.sale_order_line_id.id, product_id = intervention_product.product_id.id, sale_order_id = intervention_product.intervention_id.sale_order_id.id, installation_id = intervention.installation_id.id)
                elif intervention_product.sale_order_line_id and intervention_product.product_id.serialnumber_required:
                    raise Warning(_('Please enter %s serial number of product %s')%(str(intervention_product.sale_order_line_id.product_uom_qty), intervention_product.product_id.default_code))

        result = super(MaintenanceIntervention, self).action_done()
        return result

#When user confirm shop sale with a product with serial number required
class sale_order(models.Model):
    _inherit = 'sale.order'
    
    @api.multi
    def action_wait(self):
        res = True
        
        for order in self:
            for line in order.order_line:
                if line.product_id.serialnumber_required:
                    return {
                        'name':_("Serial numbers"),
                        'view_mode': 'form',
                        'view_type': 'form',
                        'res_model': 'serial.number.wizard',
                        'type': 'ir.actions.act_window',
                        'nodestroy': True,
                        'target': 'new',
                        'domain': '[]',
                        'context': dict(self.env.context, active_ids=self._ids)
                    }
        
        
        return res 
        
    
    ## DEPRECATED - USE action_wait() instead
    '''
    def order_confirm_elneo(self, cr, uid, ids, context):
        order = self.browse(cr, uid, ids[0], context)
        if order.shop_sale:
            for line in order.order_line:
                if line.product_id.serialnumber_required:
                    return {
                        'name':_("Serial numbers"),
                        'view_mode': 'form',
                        'view_type': 'form',
                        'res_model': 'serial.number.wizard',
                        'type': 'ir.actions.act_window',
                        'nodestroy': True,
                        'target': 'new',
                        'domain': '[]',
                        'context': dict(context, active_ids=ids)
                    }
                    
        return super(sale_order, self).order_confirm_elneo(cr, uid, ids, context)
    '''

## DEPRECATED ##
#On delivery pickings :
''' 
class stock_partial_move_memory_out(osv.osv_memory):
    _name = "stock.move.memory.out"
    _inherit = "stock.move.memory.out"
    
    _columns = {
        'serial_number':fields.char("Serial number", size=255)                
    }
stock_partial_move_memory_out()

class stock_partial_move_memory_in(osv.osv_memory):
    _name = "stock.move.memory.in"
    _inherit = "stock.move.memory.in"
    
    _columns = {
        'serial_number':fields.char("Serial number", size=255)                
    }
stock_partial_move_memory_in()
'''
    
    
class stock_transfer_details(models.TransientModel):
    _inherit = 'stock.transfer_details'

    #serial_number = fields.Char("Serial number", size=255)
    
    @api.model
    def default_get(self,fields):
        res = super(stock_transfer_details,self).default_get(fields=fields)
        if not res.has_key('item_ids'):
            return res
        
        for key, value in res.iteritems():
            if key != 'item_ids':
                continue
            
            res_items=[]
            for item in value:
                split=False
                product = self.env['product.product'].browse(item['product_id'])
                dest = self.env['stock.location'].browse(item['destinationloc_id'])
                src = self.env['stock.location'].browse(item['sourceloc_id'])
                if product.unique_serial_number and product.track_all and not dest.usage == 'inventory':
                    split = True
                if product.unique_serial_number and product.track_incoming and src.usage in ('supplier', 'transit', 'inventory') and dest.usage == 'internal':
                    split=True
                if product.unique_serial_number and product.track_outgoing and dest.usage in ('customer', 'transit') and src.usage == 'internal':
                    split=True
            
                if split:
                    items = self._split_quantities(item)
                    res_items.extend(items)
                    
                else:
                    res_items.append(item)
            
            res.update({'item_ids':res_items})
            
        return res
    
    @api.model
    def _split_quantities(self,item):
        res=[]
        if item['quantity']>1:
            item['quantity'] = (item['quantity']-1)
            new_item = item.copy()
            new_item['quantity'] = 1
            new_item['packop_id'] = False
            res.append(new_item)
            res.extend(self._split_quantities(item))
        else:
            res.append(item)
        
        return res
        
    
    @api.one
    def do_detailed_transfer(self):
        if super(stock_transfer_details,self).do_detailed_transfer():
            processed_ids = []
            # Create new and update existing pack operations
            for lstits in [self.item_ids, self.packop_ids]:
                for prod in lstits:
                    for item in prod.filtered(lambda r:r.product_id.maintenance_product):
                        for move_op in item.packop_id.linked_move_operation_ids:
                            if move_op.move_id.procurement_id.sale_line_id and move_op.move_id.procurement_id.sale_line_id.product_id:
                                self.env['maintenance.element'].create_default(item.lot_id.name, move_op.move_id.procurement_id.sale_line_id.id)  
        
        else:
            return False
        
        return True          
                
'''
class stock_partial_picking(osv.osv_memory):
    _inherit = "stock.partial.picking"
    
    def __create_partial_picking_memory(self, move, pick_type):
        result = super(stock_partial_picking, self).__create_partial_picking_memory(move, pick_type)
        
        #concat every serials with ;
        if move.sale_line_id and move.sale_line_id.maintenance_element_ids:
            for element in move.sale_line_id.maintenance_element_ids:
                if not result.has_key('serial_number'):
                    result['serial_number'] = ''
                if element.serial_number:
                    result['serial_number'] = result['serial_number'] + element.serial_number + ';'
            if result.has_key('serial_number'):
                result['serial_number'] = result['serial_number'][0:-1]
            else:
                result['serial_number'] = ''
        else:
            result['serial_number'] = ''
            
        return result
    
    def do_partial(self, cr, uid, ids, context=None):
        
        picking_ids = context.get('active_ids', False)
        wf_service = netsvc.LocalService("workflow")
        maint_elt_pool = self.pool.get("maintenance.element")
        pick_obj = self.pool.get("stock.picking")
        
        for pick in pick_obj.browse(cr, uid, picking_ids, context=context):
            #add verification of serial number and write it on maintenance element of associated line
            spp = self.browse(cr, uid, ids[0], context)
            for move in pick.move_lines:
                if move.sale_line_id and move.sale_line_id.product_id:
                    move_ids = [(partial_move.move_id.id,partial_move.serial_number) for partial_move in spp.product_moves_out]
                    for move_id in move_ids:
                        if move_id[0] == move.id:
                            if not move_id[1] or move_id[1].count(';') != move.sale_line_id.product_uom_qty - 1:
                                if move.picking_id.type == 'out' and move.sale_line_id.product_id.serialnumber_required:
                                    raise osv.except_osv(_('Processing Error'),\
                                                         _('Please enter %s serial number of product %s')%(str(move.sale_line_id.product_uom_qty), move.sale_line_id.name))
                            else:
                                maint_elt_pool.create_default(cr, uid, move_id[1], move.sale_line_id.id, context=context)
                    
        
        result = super(stock_partial_picking, self).do_partial(cr, uid, ids, context)
        return result
    
stock_partial_picking()

class stock_partial_move(osv.osv_memory):
    _inherit = "stock.partial.move"
    
    def __create_partial_move_memory(self, move):
        result = super(stock_partial_move, self).__create_partial_move_memory(move)

        result['serial_number'] = ''
                
        if move.sale_line_id and move.sale_line_id.maintenance_element_ids:
            for element in move.sale_line_id.maintenance_element_ids:
                if element.serial_number:
                    result['serial_number'] = result['serial_number'] + element.serial_number + ';'
            result['serial_number'] = result['serial_number'][0:-1]
            
        return result
    
    def do_partial(self, cr, uid, ids, context=None):
        move_ids = context.get('active_ids', False)
        spm = self.browse(cr, uid, ids, context)[0]
        
        maint_elt_pool = self.pool.get("maintenance.element")
        
        #Add serial number
        for move in self.pool.get("stock.move").browse(cr, uid, move_ids, context):
            
            if move.sale_line_id and move.sale_line_id.product_id:
                
                move_ids = [(partial_move.move_id.id, partial_move.serial_number) for partial_move in spm.product_moves_out]
                
                for move_id in move_ids:
                    if move_id[0] == move.id:
                        if not move_id[1] or move_id[1].count(';') != move.sale_line_id.product_uom_qty - 1:
                            if move.picking_id.type == 'out' and move.sale_line_id.product_id.serialnumber_required:
                                raise osv.except_osv(_('Processing Error'),\
                                                     _('Please enter %s serial number of product %s')%(move.sale_line_id.product_uom_qty, move.sale_line_id.name))
                        else:
                            maint_elt_pool.create_default(cr, uid, move_id[1], move.sale_line_id.id, context=context)
                
                move_ids = [move_id[0] for move_id in move_ids]
        
        
        result = super(stock_partial_move, self).do_partial(cr, uid, ids, context)
        pickings = [move.picking_id for move in self.pool.get("stock.move").browse(cr, uid, move_ids, context)]
       
        return result
stock_partial_move()
'''        


class maintenance_element(models.Model):
    _inherit = 'maintenance.element'
    
    def create_default(self, serial_number, sale_order_line_id=False, product_id=False, sale_order_id=False, installation_id=False):
        
        #find partner installation and create it if necessary
        def get_installation(partner, invoice_address_id, delivery_address_id):
            if partner.maintenance_installations and len(partner.maintenance_installations) == 1:
                return partner.maintenance_installations[0]
            else:
                #find if a "default" installation allready exists
                for installation in partner.maintenance_installations:
                    if installation.name == 'default':
                        return installation
                #if not found, create it
                return self.env['maintenance.installation'].create({
                        'name':'default', 
                        'partner_id':partner.id, 
                        'address_id':delivery_address_id, 
                        'invoice_address_id':invoice_address_id, 
                        #'contact_address_id':contact_address_id,                         
                    })
        
        if not serial_number:
            raise Warning(_('Serial number needed'))
        
        if not sale_order_line_id and (not product_id or not sale_order_id) and (not product_id or not installation_id):
            raise Warning( _('Can\'t find or create maintenance element without sale order line or product and sale order'))
        
        
        sale_order_line_pool = self.env['sale.order.line']
        maint_elt_pool = self.env['maintenance.element']
        year = timedelta(days=365)
        sol = False
        found = False
        maint_elt_id = False
        
        if sale_order_line_id:
            sol = sale_order_line_pool.browse(sale_order_line_id)
            
        if sol:
            partner = sol.order_id.partner_id
            invoice_address_id = sol.order_id.partner_invoice_id.id
            delivery_address_id = sol.order_id.partner_shipping_id.id
            #contact_address_id = sol.order_id.partner_order_id.id
            me_name = sol.product_id.default_code
            product_id = sol.product_id.id
        elif product_id and sale_order_id:
            product = self.env['product.product'].browse(product_id)
            order = self.env['sale.order'].browse(sale_order_id)
            partner = order.partner_id
            invoice_address_id = order.partner_invoice_id.id
            delivery_address_id = order.partner_shipping_id.id
            #contact_address_id = order.partner_order_id.id
            me_name = product.default_code
            product_id = product_id
        elif product_id and installation_id:
            product = self.env['product.product'].browse(product_id)
            installation = self.env['maintenance.installation'].browse(installation_id)
            partner = installation.partner_id
            me_name = product.default_code
            product_id = product_id
        
        product = self.env['product.product'].browse(product_id)
        
        element_type_id = False
        if product and product.maintenance_element_type_id:
            element_type_id = product.maintenance_element_type_id.id
            
        '''
        supplier_id = False
        if product and product.default_supplier_id.id:
            supplier_id = product.default_supplier_id.id
        '''
            
        #serial_numbers = serial_number.split(';')
        maint_elt_ids = []
        
        serial = serial_number
        #refresh sale order line
        sol = self.env['sale.order.line'].browse(sol.id)
        if sol and sol.maintenance_element_ids:
            for element in sol.maintenance_element_ids:
                #maintenance element linked to sale_order_line : only update serial number, and installation and warranty dates
                if (not element.serial_number or element.serial_number == serial) and (element.id not in maint_elt_ids):
                    #if partner is different, update installation
                    if element.partner_id.id != partner.id:
                        self.env['maintenance.installation'].write([element.installation_id.id], {'partner_id':partner.id, 
                                'address_id':delivery_address_id, 
                                'invoice_address_id':invoice_address_id, 
                                #'contact_address_id':contact_address_id
                                })
                    
                    maint_elt_id = element.id
                    maint_elt_pool.write([maint_elt_id], 
                         {'serial_number':serial, 
                          'installation_date':datetime.now().strftime('%Y-%m-%d'), 
                          'warranty_date':(datetime.now()+year).strftime('%Y-%m-%d'),
                          'serialnumber_required':True,
                          'element_type_id':element_type_id,
                          #'supplier_id':supplier_id 
                          }
                         )
                    found = True
                    break
        else:
            #search through existing maintenance elements any with the same serial number and link it to the customer
            maint_elements = maint_elt_pool.search([('serial_number', '=', serial)])
            if len(maint_elements) > 1:
                raise Warning(_('There are %s lines with the same serial number') % len(maint_elements))
            elif len(maint_elements) == 1:
                maint_elt_id = maint_elements[0]
                
                maint_element = maint_elt_pool.browse(maint_elements[0]) 
                
                elt = {
                  'serial_number':serial, 
                  'name':me_name, 
                  'product_id':product_id,
                  'installation_date':datetime.now().strftime('%Y-%m-%d'), 
                  'warranty_date':(datetime.now()+year).strftime('%Y-%m-%d'),
                  'serialnumber_required':True, 
                  'sale_order_line_id':sale_order_line_id,
                  'element_type_id':element_type_id,
                  #'supplier_id':supplier_id,
                  }
                
                #if partner is different, change installation
                if maint_element.partner_id.id != partner.id:
                    elt['installation_id'] = get_installation(partner, invoice_address_id, delivery_address_id)
                
                maint_elt_pool.write([maint_elt_id], elt)
                
                found = True
        
        if not found:
            #if not any maintenance element found create it
            if not installation_id:
                installation_id = get_installation(partner, invoice_address_id, delivery_address_id)
            maint_elt_id = maint_elt_pool.create({
                'installation_id':installation_id.id,
                'serial_number':serial, 
                'name':me_name, 
                'product_id':product_id, 
                'installation_date':datetime.now().strftime('%Y-%m-%d'), 
                'warranty_date':(datetime.now()+year).strftime('%Y-%m-%d'), 
                'serialnumber_required':True, 
                'sale_order_line_id':sale_order_line_id, 
                'element_type_id':element_type_id,
                #'supplier_id':supplier_id,
                })
        
        maint_elt_ids.append(maint_elt_id)
            
        return maint_elt_ids
    
    def _get_pickings(self, cr, uid, ids, field_name, arg, context=None):
        maint_elmts = self.browse(cr, uid, ids)
        res = {}
        for maint_elmt in maint_elmts:
            res[maint_elmt.id] = set([stock_move.picking_id.id for stock_move in maint_elmt.stock_moves if stock_move.picking_id.is_maint_reservation and stock_move.product_qty])
        return res
    
    stock_moves = fields.One2many('stock.move', 'maint_element_id', 'Moves')
    stock_pickings = fields.One2many(compute=_get_pickings, obj='stock.picking', string="Pickings")
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale line', help='Sale order line of sale of the element.')
    

class sale_order_line(models.Model):
    _name = 'sale.order.line'
    _inherit = 'sale.order.line'
    
    maintenance_element_ids=fields.One2many('maintenance.element', 'sale_order_line_id', string="Maintenance element", help='Maintenance elements created when this order has been sold.')
    
    
    @api.model
    def create(self, vals):
        #prevent copy of maintenance element when copy sale order
        if self.env.context and '__copy_data_seen' in self.env.context:
            vals['maintenance_element_ids'] = []
        return super(sale_order_line, self).create(vals)
