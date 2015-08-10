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

from openerp import models, fields, api, _

class maintenance_intervention_product(models.Model):
    _inherit = 'maintenance.intervention.product'
    
    @api.one
    def _qty_virtual_stock(self):
        
        if self.product_id:
            if self.intervention_id and self.intervention_id.sale_order_id:
                warehouse = self.intervention_id.sale_order_id.warehouse_id
            else:
                warehouse = self.env.user.default_warehouse_id
            
            if warehouse:    
                self.virtual_stock = self.product_id.with_context(location=warehouse.lot_stock_id.id).virtual_available
            else:
                self.virtual_stock = 0
        else:
            self.virtual_stock = 0
        
    
    @api.one
    def _qty_real_stock(self):
        if self.product_id:
            if self.intervention_id and self.intervention_id.sale_order_id:
                warehouse = self.intervention_id.sale_order_id.warehouse_id
            else:
                warehouse = self.env.user.default_warehouse_id
            
            if warehouse:    
                self.real_stock = self.product_id.with_context(location=warehouse.lot_stock_id.id).qty_available
            else:
                self.real_stock = 0
        else:
            self.real_stock = 0
   
    virtual_stock = fields.Float(compute=_qty_virtual_stock,  string='Virtual stock')
    real_stock = fields.Float(compute=_qty_real_stock,  string='Real stock')
    
    
class maintenance_installation(models.Model):
    _inherit='maintenance.installation'
    
    maintenance_product_description=fields.Text("Maintenance products description")
    
    
class sale_order(models.Model):
    _inherit='sale.order'
    
    @api.multi
    def action_button_confirm(self):
        for sale in self:
            if not sale.shop_sale:
                for line in sale.order_line:
                    if line.product_id.maintenance_product and len(line.maintenance_element_ids) < line.product_uom_qty:
                        dummy, view_id = self.env['ir.model.data'].get_object_reference('elneo_maintenance', 'view_wizard_sale_confirm')
                        
                        context = self.env.context.copy()
                        context['partner_id'] = sale.partner_id.id
                        context['sale_id'] = sale.id 
                        return {
                                'name':_("Sale confirm"),
                                'view_mode': 'form',
                                'view_id': [view_id], 
                                'view_type': 'form',
                                'res_model': 'wizard.sale.confirm',
                                'type': 'ir.actions.act_window',
                                'target': 'new',
                                'nodestroy':True, 
                                'context':context
                            }
            
        return super(sale_order, self).action_button_confirm()
   
'''
class maintenance_installation(osv.osv):
    _inherit = 'maintenance.installation'
    
    def onchange_address_id(self, cr, uid, ids, address_id, context=None):
        user_pool = self.pool.get("res.users")
        if address_id:
            seller_id = self.pool.get("sale.order").find_sale_man_id(cr, uid, address_id, 10)
            if not seller_id:
                seller_id = self.pool.get("sale.order").find_sale_man_id(cr, uid, address_id, 11)
            if seller_id:
                shop_id = user_pool.browse(cr, uid, seller_id, context=context).shop_id.id
                return {'value':{'shop_id':shop_id}}
        return {}
    
    
    
    
maintenance_installation()



class maintenance_element_brand(osv.osv):
    _name='maintenance.element.brand'
    _columns={
        'name':fields.char(size=255, string="Name")
    }
maintenance_element_brand()


class maintenance_element(osv.osv):
    _inherit = 'maintenance.element'
    
    def import_timeofuse(self,cr,uid,ids,context=None):
        
        return {
                'name':_("Import time of use"),
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'maintenance.element.timeofuse.wizard',
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': '[]',
                'context': dict(context, active_ids=ids)
            }
        
    def _is_under_project(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for element in self.browse(cr, uid, ids, context):
            res[element.id] = False
            for project in element.maintenance_projects:
                if project.active:
                    for project_elt in project.maintenance_elements:
                        if project_elt.id == element.id: 
                            res[element.id] = True
                break
        return res
                 
    def get_elements_from_project(self, cr, uid, ids, c={}):
        res = []
        for project in self.pool.get("maintenance.project").browse(cr, uid, ids, c):
            for element in project.maintenance_elements:
                res.append(element.id)
        return res
                                                        
    
    _columns = {
        'brand':fields.many2one('maintenance.element.brand', string="Brand"), 
        'power':fields.float("Power (kW)"),
        'maintenance_partner':fields.char(string="Maintenance partner", size=255), 
        'under_competitor_contract':fields.boolean("Under competitor contract"), 
        'end_of_current_contract':fields.date('End of current contract'), 
        'supplier_id':fields.many2one('res.partner', string='Supplier'),
        'under_project':fields.function(_is_under_project, type='boolean', string="Under project", method=True, readonly=True, 
                                        store={'maintenance.project': (get_elements_from_project, ['maintenance_elements'], 20),})
                
    } 
    
    _defaults = {
        'main_element':lambda self, cr, uid, context : context['default_main'] if context and 'default_main' in context else False 
    }
    
maintenance_element()



class sale_order(osv.osv):
    _inherit = 'sale.order'
    
    def write(self, cr, uid, ids, vals, context=None):
        if vals.get("intervention_id",False):
            vals['disable_automatic_landefeld'] = True
        return super(sale_order, self).write(cr, uid, ids, vals, context=context)
    
    def create(self, cr, user, vals, context=None):
        if vals.get("intervention_id",False):
            vals['disable_automatic_landefeld'] = True
        return super(sale_order, self).create(cr, user, vals, context=context)
    
    def order_confirm_elneo(self, cr, uid, ids, context):
        for sale in self.browse(cr, uid, ids, context):
            if not sale.shop_sale:
                for line in sale.order_line:
                    if line.product_id.maintenance_product and len(line.maintenance_element_ids) < line.product_uom_qty:
                        dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'elneo_maintenance', 'view_wizard_sale_confirm')
                        if not context:
                            context = {}
                        context['partner_id'] = sale.partner_id.id
                        context['sale_id'] = sale.id 
                        return {
                                'name':_("Sale confirm"),
                                'view_mode': 'form',
                                'view_id': [view_id], 
                                'view_type': 'form',
                                'res_model': 'wizard.sale.confirm',
                                'type': 'ir.actions.act_window',
                                'target': 'new',
                                'nodestroy':True, 
                                'context':context
                            }
            
        return super(sale_order, self).order_confirm_elneo(cr, uid, ids, context=context)
        
sale_order()

class maintenance_intervention(osv.osv):
    _inherit = 'maintenance.intervention' 
    
    _columns = {
        'blocked' : fields.related('partner_id','blocked', string='Customer blocked', type="boolean"), 
        'shop_id':fields.related('sale_order_id','shop_id', type="many2one", relation="sale.shop", string="Shop"),         
        'installation_shop_id':fields.related('installation_id','shop_id', type="many2one", relation="sale.shop", string="Shop"),
        'create_uid': fields.many2one('res.users', 'Creation user', readonly=True),
        'write_uid':  fields.many2one('res.users', 'Last Modification User', readonly=True),
        'installation_zip':fields.related('installation_id','address_id','zip',type="char",size=255, string="Zip", store=True),
        'error_status':fields.selection([('potentially','Potentially Available'),('delivery_outdated','Purchase Delivery Outdated'),('no_purchase','No Purchase'),('no_input','No Input Linked(On Order)'),('picking_error','Picking Error'),('sale_incident','Sale Incident'),('purchase_incident','Purchase Incident'),('elneo_supplier','Elneo is Supplier'),('not_enough_stock', 'Not enough stock')],string='Error Status')
    }
    
    _defaults={'error_status':False}
    
    # TO CHECK
    #_order = 'date_scheduled desc NULLS LAST'
    
    def write(self, cr, uid, ids, vals, context={}):
        res = super(maintenance_intervention, self).write(cr, uid, ids, vals, context)
        if 'contact_address_id' in vals:
            sale_order_pool = self.pool.get("sale.order")            
            for intervention in self.browse(cr, uid, ids, context):
                if intervention.sale_order_id:
                    sale_order_pool.write(cr, uid, [intervention.sale_order_id.id], {'quotation_address_id':vals['contact_address_id']}, context=context)
        return res
    
    #Function to determine which error status set to the intervention
    def set_error_status(self,cr,uid, context=None):
        if not context:
            context={}
            
        ids = self.search(cr,uid,[('state','=','confirmed')],context)
        for intervention in self.browse(cr,uid,ids,context):
            
            #We reset the error
            error = False
            val = {'error_status':None}
            
            #We create a temp dict to manage, at the end, the error priority
            result={'purchase_incident':False,
                    'no_input':False,
                    'potentially':False,
                    'no_purchase':False,
                    'sale_incident':False,
                    'delivery_outdated':False,
                    'elneo_supplier':False,
                    'picking_error':False,
                    'not_enough_stock':False, #line make_to_stock, unavailable, with virtual stock < requested quantity
                    }

            # We look for receptions that are not done and for which products are in stock (real)    
            if intervention.sale_order_id.purchase_orders:
                for purchase_order in intervention.sale_order_id.purchase_orders:
                    
                    if purchase_order.state in ('except_picking'):
                        result.update({'purchase_incident':True})
                        #error=True
                        #break
                    if purchase_order.minimum_planned_date < intervention.date_scheduled:
                        result.update({'delivery_outdated':True})
                    
                    if not purchase_order.picking_ids:
                        result.update({'no_input':True})
                        #error=True
                    for picking in purchase_order.picking_ids:
                        
                        
                        if picking.type=='in' and picking.state in ('assigned'):
                            for stock_move in picking.move_lines :
                                if (stock_move.state == 'assigned'):
                                    context.update({'product_id':stock_move.product_id.id})
                                    stock = self.pool.get('stock.location')._product_value(cr, uid, [stock_move.location_dest_id.id],['stock_real'],None, context=context)
                                    if stock_move.product_qty <= stock[stock_move.location_dest_id.id]['stock_real']:
                                        result.update({'potentially':True})
                                else:
                                    result.update({'picking_error':True})
                        
                        if picking.type=='in' and picking.state in ('done'):
                            for stock_move in picking.move_lines :
                                if (stock_move.state != 'done'):
                                    result.update({'picking_error':True})
                                    
                                        
            
            else:
                #We look for products on order
                if intervention.sale_order_id.order_line:
                    for order_line in intervention.sale_order_id.order_line:
                        if order_line.type == 'make_to_order':
                            result.update({'no_purchase':True})
                            # We detect if no purchase and product has supplier Elneo
                            if order_line.product_id:
                                suppinfo_ids = self.pool.get('product.supplierinfo').search(cr,uid,[('product_id','=',order_line.product_id.id)], order='sequence')
                                if suppinfo_ids:
                                    suppinfo = self.pool.get('product.supplierinfo').browse(cr, uid, suppinfo_ids[0], context=context)
                                    if suppinfo.name.id == 1:
                                        result.update({'elneo_supplier':True})
                        
                        #find related stock move
                        for picking in intervention.sale_order_id.picking_ids:
                            if picking.type == 'internal':
                                move_ids = self.pool.get("stock.move").search(cr, uid, [('picking_id','=',picking.id), ('state','=','confirmed')], context=context)
                                moves = self.pool.get("stock.move").browse(cr, uid, move_ids, context=context)
                                for move in moves:
                                    #check virtual stock
                                    c = context.copy()
                                    c.update({ 'states': ('confirmed','waiting','assigned','done'), 'what': ('in', 'out'), 'warehouse':intervention.sale_order_id.shop_id.warehouse_id.id})
                                    res_stock = self.pool.get("product.product").get_product_available(cr, uid, [move.product_id.id], context=c)
                                    virtual_stock = res_stock.get(move.product_id.id, 0.0)
                                    if virtual_stock < move.product_qty:
                                        result.update({'not_enough_stock':True})
            
            # If sale order is in incident
            if not error and (intervention.sale_order_id.state and intervention.sale_order_id.state in ('shipping_except')):
                result.update({'sale_incident':True})
                
                    
            # We manage the error priority
            if result['potentially']:
                val.update({'error_status':'potentially'})
                
            elif result['delivery_outdated']:
                val.update({'error_status':'delivery_outdated'})

            elif result['no_input']:
                val.update({'error_status':'no_input'})

            elif result['sale_incident']:
                val.update({'error_status':'sale_incident'})
                
            elif result['elneo_supplier']:
                val.update({'error_status':'elneo_supplier'})
                
            elif result['purchase_incident']:
                val.update({'error_status':'purchase_incident'})
                
            elif result['picking_error']:
                val.update({'error_status':'picking_error'})
                
            elif result['not_enough_stock']:
                val.update({'error_status':'not_enough_stock'})
            
            
                
            self.write(cr,uid,[intervention.id],val)
                            
        # We reset the error status for other interventions
        ids_to_null = self.search(cr,uid,[('state','!=','confirmed'),('error_status','!=',False)],context=context)
        self.write(cr,uid,ids_to_null,{'error_status':False})
        
        return True
        
    
    def get_sale_default_values(self, cr, uid, partner, intervention, context):
        res = super(maintenance_intervention, self).get_sale_default_values(cr, uid, partner, intervention, context)
        if context.get("quotation",False) and intervention and intervention.contact_address_id:
            res['quotation_address_id'] = intervention.contact_address_id.id
        return res
    
    #Cancel intervention without sale_order
    def action_convert_delivery(self, cr, uid, ids, context=None):
        #cancel interventions
        self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
        return True
    
    def generate_invoice(self, cr, uid, ids, context):
        res = super(maintenance_intervention, self).generate_invoice(cr, uid, ids, context)
        
        #manage cost price of invoice lines and section_id of invoice
        if res:
            invoice_line_pool = self.pool.get("account.invoice.line")
            invoice_pool = self.pool.get("account.invoice")
            for invoice in invoice_pool.browse(cr, uid, res, context=context):
                #set cost price from sale order line if exist or from product else
                for invoice_line in invoice.invoice_line:
                    if invoice_line.sale_order_lines:
                        invoice_line_pool.write(cr, uid, [invoice_line.id], {"cost_price":invoice_line.sale_order_lines[0].purchase_price}, context=context)
                    else:
                        invoice_line_pool.write(cr, uid, [invoice_line.id], {"cost_price":invoice_line.product_id.cost_price}, context=context)
                        
                #set section_id of sale order
                if invoice.sale_order_ids:
                    invoice_pool.write(cr, uid, [invoice.id], {'section_id':invoice.sale_order_ids[0].section_id.id}, context=context)
        
        return res
                        
            
        
    
    #add flash info when selecting installation in intervention
    def on_change_installation_id(self, cr, uid, ids, installation_id=None):
        
        res = super(maintenance_intervention, self).on_change_installation_id(cr, uid, ids, installation_id)
        
        if not res:
            res = {}
                                              
        warning = {}
        title = ''
        message = ''
        
        if not installation_id:
            return {}
        else:
            part = self.pool.get("maintenance.installation").browse(cr, uid, installation_id).partner_id
            
        title = ''
        
        if part.blocked:
            title =  _("Attention: the client is blocked")+'\n' 
            message = _("Attention: the client is blocked")+'\n'
            
        if part.flash_info == True:
            title =  title+_("Flash information")
            message = message+"%s" % (part.flash_info_content)
        
        if title:
            warning = {
                    'title': title,
                    'message': message,}
        
            warning['title'] = title
            warning['message'] = message
                        
            res['warning'] = warning
        
        return res
    
    def action_done(self, cr, uid, ids, context=None):
        result = super(maintenance_intervention, self).action_done(cr, uid, ids, context)
        
        #if a popup must shown, show it
        if type(result) == dict and result.get("type") == 'ir.actions.act_window':
            return result
        
        res_users_pool = self.pool.get("res.users")
        
        me = res_users_pool.browse(cr, uid, uid, context=context) 
        
        for intervention in self.browse(cr, uid, ids, context=context):
            if intervention.int_comment:
                request =  self.pool.get('res.request')
                users_to_send_request = [user for user in res_users_pool.browse(cr, uid, res_users_pool.search(cr, uid, [('context_section_id', '=', me.context_section_id.id)]), context) if user.receive_warehouse_request]
                
                subject = 'End of intervention '+intervention.code+(intervention.name and '('+intervention.name+')' or '')+' for '+intervention.installation_id.name_get()[0][1]
                body = ""
                
                if intervention.int_comment:
                    body = body+'Internal comment : \n'+intervention.int_comment
                
                if intervention.ext_comment:
                    body = body+'\n External Comment : \n'+intervention.ext_comment
                    
                for user in users_to_send_request:
                    request.create(cr, uid, 
                        {
                         'name':subject,
                         'body':body,
                         'act_from': uid,
                         'act_to': user.id,
                         'state' : 'waiting',
                        })
        
        return { 
                    'type': 'ir.actions.report.xml',
                    'report_name':'report.maintenance.intervention',
                    'nodestroy': True,
                    'datas':{'model':'maintenance.intervention', 'ids': ids},
                } 

maintenance_intervention()

class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    
    def _get_installation(self, cr, uid, ids, field_names, args, context=None):
        res = {}
        for pick in self.browse(cr, uid, ids, context):
            res[pick.id] = {}
            if pick.sale_id and pick.sale_id.intervention_id:
                if 'is_maint_reservation' in field_names:
                    res[pick.id]['is_maint_reservation'] = True
                if 'installation_id' in field_names:
                    if pick.sale_id.intervention_id.state != 'cancel':
                        res[pick.id]['installation_id'] = pick.sale_id.intervention_id.installation_id.id
                    else:
                        res[pick.id]['installation_id'] = None
            else: 
                if 'is_maint_reservation' in field_names:
                    res[pick.id]['is_maint_reservation'] = False
        return res
    
    def _get_reservation_by_sale_order(self, cr, uid, ids, context=None):
        res = []
        for sale in self.pool.get("sale.order").browse(cr, uid, ids, context):
            res.extend([pick.id for pick in sale.picking_ids])
        return res
    
    def _get_reservation_by_intervention(self, cr, uid, ids, context=None):
        res = []
        for intervention in self.pool.get("maintenance.intervention").browse(cr, uid, ids, context):
            if intervention.sale_order_id.id:
                res.extend(self.pool.get("stock.picking")._get_reservation_by_sale_order(cr, uid, [intervention.sale_order_id.id], context))
        return res
    
    _columns={
        'is_maint_reservation':fields.function(_get_installation, string='Maintenance reservation', type="boolean", method=True, store={
                'sale.order': (_get_reservation_by_sale_order, ['intervention_id'], 20),
                'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['sale_id'], 20),
                'maintenance.intervention':(_get_reservation_by_intervention, ['sale_order_id','state'], 10)
            }, multi='installation'),
               
        'maint_color':fields.related('sale_id', 'intervention_id', 'maint_type', 'color', type='char', size=255, string='Color (maintenance)'),  
        'maint_type':fields.related('sale_id', 'intervention_id', 'maint_type', type='many2one', relation='maintenance.intervention.type', string="Maintenance type"),
        'installation_id':fields.function(_get_installation, string="Installation", type='many2one', method=True, relation='maintenance.installation', multi='installation', store={
            'sale.order': (_get_reservation_by_sale_order, ['intervention_id'], 20),
            'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['sale_id'], 20),
        }), 
    }
stock_picking()

class stock_move(osv.osv):
    _inherit = 'stock.move'
    def unlink(self, cr, uid, ids, context=None):
        #bypass draft verification if we delete maintenance move
        try:
            return super(stock_move, self).unlink(
                cr, uid, ids, context=context)
        except osv.except_osv, e:
            if e.value == _('You can only delete draft moves.'): 
                for move in self.browse(cr, uid, ids, context=context):
                    if move.picking_id and move.picking_id.sale_id and move.picking_id.sale_id.intervention_id:
                        return super(osv.osv,self).unlink(cr, uid, ids, context=context)
            raise e
        
    def get_is_purchased(self, cr, uid, ids, field_names, args, context=None):
        res = {}
        for move_id in ids: 
            if self.search(cr, uid, [('move_dest_id','=',move_id)], context=context):
                res[move_id] = True
            else:
                res[move_id] = False
        return res
    
    #sale_price and purchased are used in reservation report
    _columns = {
        'sale_price':fields.related('sale_line_id', 'price_unit', type='float', string="Sale price"), 
        'purchased':fields.function(get_is_purchased, type="boolean", size=255, method=True, string="Is purchased", store=True)
    }
stock_move()




class create_project_sales_wizard(osv.osv_memory):
    _name = "elneo_maintenance.create_project_sales_wizard"
    
    _columns = {
    }
    
    def create_project_sales(self, cr, uid, ids, context=None):
        cr = pooler.get_db(cr.dbname).cursor()
        logger = netsvc.Logger()
        commit_counter = datetime.now()
        commit_time = 1  
        
        i = 0
        begining = datetime.now()
        wizards = self.browse(cr, uid, ids, context)
        log = ''
        
        logger.notifyChannel('Create project sales', netsvc.LOG_ERROR, '------ Begin ------')
        
        maintenance_project_pool = self.pool.get("maintenance.project")        
        sale_order_pool = self.pool.get("sale.order")
        
        try:
            for wizard in wizards:
                project_ids = maintenance_project_pool.search(cr, uid, [('sale_order_id','=',None),('next_invoice_date','>=','2013-08-01'),('enable','=',True)], context=context)
                project_ids = project_ids[0:100]
                res = maintenance_project_pool.action_create_update_sale_order(cr, uid, project_ids, context=context)
        except Exception,e:
                logger.notifyChannel('Create project sales', netsvc.LOG_ERROR, 'ERREUR !!!')
                logger.notifyChannel('Create project sales', netsvc.LOG_ERROR, 'e = '+unicode(e))      
        finally:
            try:                
                cr.commit()
                logger.notifyChannel('Create project sales', netsvc.LOG_ERROR, '------ Commit Final ------')
            except Exception:
                pass
            try:                
                cr.close()
            except Exception:
                pass
            
        return True
    
    
    def action_create_project_sales(self, cr, uid, ids, context=None):
        thread_update_product_prices = threading.Thread(target=self.create_project_sales, args=(cr, uid, ids, context))
        thread_update_product_prices.start()
        return {'type': 'ir.actions.act_window_close'}

create_project_sales_wizard()

class create_installations_wizard(osv.osv_memory):
    _name = "elneo_maintenance.create_installations_wizard"
    
    _columns = {
    }
    
    def create_installations(self, cr, uid, ids, context=None):
        cr = pooler.get_db(cr.dbname).cursor()
        logger = netsvc.Logger()
        commit_counter = datetime.now()
        commit_time = 1  
        
        i = 0
        begining = datetime.now()
        wizards = self.browse(cr, uid, ids, context)
        log = ''
        
        logger.notifyChannel('Import maintenance installation', netsvc.LOG_ERROR, '------ Begin ------')
        
        maintenance_installation_pool = self.pool.get("maintenance.installation")
        maintenance_element_pool = self.pool.get("maintenance.element")
        address_pool = self.pool.get("res.partner.address")
        product_pool = self.pool.get("product.product")
        
        def hasCompressorCat(product, cat=None):
            if not cat:
                return hasCompressorCat(product, product.categ_id)
            elif cat.id == 9891:
                return True
            elif not cat.parent_id:
                return False
            else:
                return hasCompressorCat(product, cat.parent_id)
        
        try:
            for wizard in wizards:
                cr.execute("select delivery_address_id, array_to_string(array_agg(id),',') from maintenance_element where installation_id is null group by delivery_address_id")
                lines = cr.fetchall()
                total = len(lines)
                i = 0
                for line in lines:
                    i = i+1
                    timetodoi = datetime.now() - begining
                    todo = total-i
                    timeremaining = timetodoi*todo/i
                    logger.notifyChannel('Import maintenance installation', netsvc.LOG_INFO, '::: '+str(i)+'/'+str(total)+' : remaining '+unicode(timeremaining)+'| since '+unicode(timetodoi))
                    
                    if (datetime.now() - commit_counter).seconds  > commit_time*60:
                            commit_counter = datetime.now()
                            cr.commit()
                            logger.notifyChannel('Update product price', netsvc.LOG_INFO, '----- Commit 2 -----')
                    
                    delivery_address = address_pool.browse(cr, uid, line[0], context=context)
                    element_ids = [int(e) for e in line[1].split(',')]
                    elements = maintenance_element_pool.browse(cr, uid, element_ids, context=context)
                    
                    maintenance_product_description = ''
                    
                    primary_element = None
                    secondary_element = None
                    invoice_address_id = None
                    invoice_address_id_bis = None
                    if len(elements) == 1:
                        primary_element = elements[0]
                        if primary_element.description:
                            maintenance_product_description = primary_element.description
                        else:
                            maintenance_product_description = primary_element.piece_tmi
                        invoice_address_id_bis = primary_element.invoice_address_id.id
                    else:
                        description = ''
                        piece_tmi = False
                        for element in elements:
                            if element.invoice_address_id and not invoice_address_id:
                                invoice_address_id = element.invoice_address_id.id
                            
                            if element.description:
                                description = description+'\r\n'+element.description
                            if not piece_tmi and element.piece_tmi:
                                piece_tmi = element.piece_tmi
                                
                            if element.product_id and not primary_element:
                                if hasCompressorCat(element.product_id):
                                    primary_element = element
                                    if not invoice_address_id:
                                        invoice_address_id = primary_element.invoice_address_id.id
                            elif element.name and not secondary_element:
                                #find product with the same name
                                product_ids = product_pool.search(cr, uid, [('default_code','ilike',element.name)])
                                if not product_ids:
                                    product_ids = product_pool.search(cr, uid, [('name','ilike',element.name)])
                                if product_ids:
                                    for product in product_pool.browse(cr, uid, product_ids, context=context):
                                        if  not secondary_element and hasCompressorCat(product):
                                            secondary_element = element
                        if description:
                            maintenance_product_description = description
                        else:
                            maintenance_product_description = piece_tmi
                    
                    name = ''
                    if primary_element:
                        name = primary_element.name
                    elif secondary_element:
                        name = secondary_element.name
                    
                    if not invoice_address_id:
                        invoice_address_id = invoice_address_id_bis
                    
                    if delivery_address and delivery_address.partner_id:
                        installation_id = maintenance_installation_pool.create(cr, uid, {'name':name, 'partner_id':delivery_address.partner_id.id, 'address_id':delivery_address.id, 'invoice_address_id':invoice_address_id, 'maintenance_product_description':maintenance_product_description})
                        maintenance_element_pool.write(cr, uid, element_ids, {'installation_id':installation_id}, context=context)
        except Exception,e:
                logger.notifyChannel('Import maintenance installation', netsvc.LOG_ERROR, 'ERREUR !!!')
                logger.notifyChannel('Import maintenance installation', netsvc.LOG_ERROR, 'e = '+unicode(e))      
        finally:
            try:                
                cr.commit()
                logger.notifyChannel('Import maintenance installation', netsvc.LOG_ERROR, '------ Commit Final ------')
            except Exception:
                pass
            try:                
                cr.close()
            except Exception:
                pass
            
        return True
    
    
    def action_create_installations(self, cr, uid, ids, context=None):
        thread_update_product_prices = threading.Thread(target=self.create_installations, args=(cr, uid, ids, context))
        thread_update_product_prices.start()
        return {'type': 'ir.actions.act_window_close'}

create_installations_wizard()


class create_interventions_wizard(osv.osv_memory):
    _name = "elneo_maintenance.create_interventions_wizard"
    
    _columns = {
    }
    
    def create_interventions(self, cr, uid, ids, context=None):
        
        def find_address(partner_id):
            partner = self.pool.get("res.partner").browse(cr, uid, partner_id, context=context)
            res = {}
            default = 0
            for address in partner.address:
                if not res.has_key("invoice") and address.type == 'invoice':
                    res['invoice']=address.id
                elif not res.has_key("contact") and address.type == 'contact':
                    res['contact'] = address.id
                elif not res.has_key("delivery") and address.type == 'delivery':
                    res['delivery'] = address.id
                elif not default and address.type == 'default':
                    default = address.id
            
            if default:    
                if not res.has_key("invoice"):
                    res['invoice'] = default
                if not res.has_key("contact"):
                    res['contact'] = default
                if not res.has_key("delivery"):
                    res['delivery'] = default
                    
            if not res.has_key("invoice"):
                res['invoice'] = None
            if not res.has_key("contact"):
                res['contact'] = None
            if not res.has_key("delivery"):
                res['delivery'] = None
            
            
            return res
                
                 
        
        cr = pooler.get_db(cr.dbname).cursor()
        logger = netsvc.Logger()
        commit_counter = datetime.now()
        commit_time = 1  
        
        i = 0
        begining = datetime.now()
        wizards = self.browse(cr, uid, ids, context)
        log = ''
        
        logger.notifyChannel('Import maintenance intervention', netsvc.LOG_ERROR, '------ Begin ------')
        
        maintenance_intervention_pool = self.pool.get("maintenance.intervention")
        maintenance_intervention_product_pool = self.pool.get("maintenance.intervention.product")
        maintenance_installation_pool = self.pool.get("maintenance.installation")
        maintenance_element_pool = self.pool.get("maintenance.element")
        address_pool = self.pool.get("res.partner.address")
        product_pool = self.pool.get("product.product")
        picking_pool = self.pool.get("stock.picking")
        task_pool = self.pool.get("maintenance.intervention.task")
        
        try:
            for wizard in wizards:
                
                #ATTENTION : delete ('technician','!=',False)
                old_intervention_ids = picking_pool.search(cr, uid, [('is_maint_reservation','=',True),('type','=','out'),('state','!=','cancel')], context=context, order='id')
                #old_intervention_ids = [14493]
                
                intervention_ids = []
                intervention_done_ids = []
                
                install_move = 0
                install_address = 0
                install_partner = 0
                install_partner_sup = 0
                install_not_found = 0
                
                #create intervention
                
                old_interventions = picking_pool.browse(cr, uid, old_intervention_ids, context=context)
                total = len(old_interventions)
                
                for old_intervention in old_interventions:
                    
                    i = i+1
                    timetodoi = datetime.now() - begining
                    todo = total-i
                    timeremaining = timetodoi*todo/i
                    
                    installation_ids = []
                    
                    for move in old_intervention.move_lines:
                        if move.maint_element_id:
                            installation_ids = [move.maint_element_id.installation_id.id]
                    if not installation_ids:        
                        installation_ids = maintenance_installation_pool.search(cr, uid, [('address_id','=',old_intervention.address_id.id)], context=context)
                        if not installation_ids:
                            installation_ids = maintenance_installation_pool.search(cr, uid, [('partner_id','=',old_intervention.sale_id.partner_id.id)], context=context)
                            if not installation_ids:
                                install_not_found = install_not_found + 1
                            elif len(installation_ids) > 0:
                                install_partner_sup = install_partner_sup + 1 
                            else:
                                install_partner = install_partner + 1
                        else:
                            install_address = install_address + 1
                    else:
                        install_move = install_move + 1
                        
                    logger.notifyChannel('Import maintenance intervention', netsvc.LOG_INFO, '::: '+str(i)+'/'+str(total)+' : remaining '+unicode(timeremaining)+'| since '+unicode(timetodoi)+" | install_move = "+str(install_move)+" | install_address = "+str(install_address)+" | install_partner = "+str(install_partner)+" | many_install = "+str(install_partner_sup)+" | no_install = "+str(install_not_found))                
                    
                    sale_order_id = old_intervention.sale_id.id
                    
                    #installation not found : create installation for customer
                    if not installation_ids:
                        partner_id = old_intervention.sale_id.partner_id.id
                        addresses = find_address(partner_id)
                        installation_ids = [maintenance_installation_pool.create(cr, uid, {
                                'partner_id':old_intervention.sale_id.partner_id.id, 
                                'address_id':addresses['delivery'], 
                                'invoice_address_id':addresses['invoice'], 
                                'contact_address_id':addresses['contact']
                            }, context=context)]
                        
                        maintenance_installation_pool.write(cr, uid, installation_ids, {'name':maintenance_installation_pool.browse(cr, uid, installation_ids)[0].code})
                        
                    if installation_ids and sale_order_id:
                        installation_id = installation_ids[0]
                        installation = maintenance_installation_pool.browse(cr, uid, installation_id, context=context)
                        intervention_state = 'done'
                        if old_intervention.state != 'done':
                            intervention_state = 'confirmed'
                            
                        maint_type_id = 1
                        if old_intervention.sale_id.maint_type == "maintenance":
                            maint_type_id = 1
                        if old_intervention.sale_id.maint_type == "assembly":
                            maint_type_id = 2
                        if old_intervention.sale_id.maint_type == "reparation":
                            maint_type_id = 3
                        if old_intervention.sale_id.maint_type == "audit":
                            maint_type_id = 4
                            
                        if old_intervention.sale_id.partner_order_id:
                            contact_address_id = old_intervention.sale_id.partner_order_id.id
                        else:
                            contact_address_id = None
                        
                        
                        intervention_id = maintenance_intervention_pool.create(cr, uid, {
                                                                        'name':old_intervention.note, 
                                                                       'installation_id':installation_id,
                                                                       'int_comment':old_intervention.int_comment,
                                                                       'ext_comment':old_intervention.ext_comment,  
                                                                       'maint_type':maint_type_id, 
                                                                       'contact_address_id':contact_address_id, 
                                                                       'sale_order_id':sale_order_id
                        })
                        
                        intervention_ids.append(intervention_id)
                        if intervention_state == 'done':
                            intervention_done_ids.append(intervention_id)
                        
                cr.commit()
                
                #picking_ids = picking_pool.search(cr, uid, [('technician','!=',False)], context=context)
                #intervention_ids = [pick.sale_id.intervention_id.id for pick in picking_pool.browse(cr, uid, picking_ids, context=context) if pick.sale_id and pick.sale_id.intervention_id]
                #intervention_ids = intervention_ids[0:30]
                
                maintenance_intervention_pool.action_confirm(cr, uid, intervention_ids, context=context)
                
                cr.commit()
                

                i = 0
                interventions = maintenance_intervention_pool.browse(cr, uid, intervention_ids, context=context)
                total = len(interventions)
                int_without_out_picking = 0
                
                
                for intervention in interventions:
                    i = i+1
                    logger.notifyChannel('Import maintenance intervention - TASK CREATION', netsvc.LOG_INFO, 'int_without_out_picking = '+str(int_without_out_picking)+' | intervention = '+str(intervention.id)+' -- '+str(i)+'/'+str(total))
                    task_id = intervention.tasks[0].id
                    
                    out_pickings = [pick for pick in intervention.stock_pickings if pick.type == 'out']
                    if out_pickings:
                        out_picking = out_pickings[0]
                        
                        if not out_picking.technician.id and out_picking.state == 'done':
                            ''
                        
                        for move in out_picking.move_lines:
                            #create maintenance products
                            description = None
                            if move.product_id:
                                description = move.product_id.name_get()[0][1]
                            intervention_product_id = maintenance_intervention_product_pool.create(cr, uid, {
                                                                                   'description':description, 
                                                                                   'intervention_id':intervention.id, 
                                                                                   'product_id':move.product_id.id, 
                                                                                   'maintenance_element_id':move.maint_element_id.id, 
                                                                                   'quantity':move.product_qty, 
                                                                                   }, context=context)
                            move_ids = self.pool.get("stock.move").search(cr, uid, [('move_dest_id','=',move.id)])
                            move_ids.append(move.id) 
                            self.pool.get("stock.move").write(cr, uid, move_ids, {'intervention_product_id':intervention_product_id}, context=context)
                            
                            #update sale_order_line:
                            self.pool.get("sale.order.line").write(cr, uid, move.sale_line_id.id, {'intervention_product_id':intervention_product_id}, context=context)
                        
                        #create task
                        date_start = out_picking.confirmed_delivery_date
                        if out_picking.maint_arrival_time:
                            date_start = out_picking.maint_arrival_time
                        
                        try:
                            task_pool.write(cr, uid, task_id, {'user_id': out_picking.technician.id, 
                                                               'date_start':date_start, 
                                                               'date_end':out_picking.maint_departure_time,
                                                               'planned_hours':out_picking.maint_operation_time/4,
                                                               'break_time':out_picking.maint_break_time/60
                                                               })
                            cr.commit()
                        except Exception,e:
                            task_pool.write(cr, uid, task_id, {'user_id': out_picking.technician.id, 
                                                               'date_start':date_start, 
                                                               'date_end':datetime.strftime(datetime.strptime(out_picking.maint_arrival_time, "%Y-%m-%d %H:%M:%S")+timedelta(hours=out_picking.maint_break_time/60),"%Y-%m-%d %H:%M:%S"),
                                                               'planned_hours':out_picking.maint_operation_time/4,
                                                               'break_time':out_picking.maint_break_time/60
                                                               })
                            cr.commit()
                            
                    else:
                        int_without_out_picking = int_without_out_picking+1
                        
                cr.commit()
                
                maintenance_intervention_pool.write(cr, uid, intervention_done_ids, {'state':'done'})
        except Exception,e:
                logger.notifyChannel('Import maintenance intervention', netsvc.LOG_ERROR, 'ERREUR !!! '+str(installation_id))                
                logger.notifyChannel('Import maintenance intervention', netsvc.LOG_ERROR, 'e = '+unicode(e)+'\n -- stacktrace = '+traceback.format_exc()) 
        finally:
            try:                
                cr.commit()
                logger.notifyChannel('Import maintenance intervention', netsvc.LOG_ERROR, '------ Commit Final ------')
            except Exception:
                pass
            try:                
                cr.close()
            except Exception:
                pass
            
        return True
    
    
    def action_create_interventions(self, cr, uid, ids, context=None):
        thread_update_product_prices = threading.Thread(target=self.create_interventions, args=(cr, uid, ids, context))
        thread_update_product_prices.start()
        return {'type': 'ir.actions.act_window_close'}

create_interventions_wizard()


class maintenance_project_initial_cpi_id_compute(osv.osv_memory):
    
    _name = 'maintenance.project.initial.cpi.compute'
    
    def compute(self, cr, uid, ids, context=None):
        project_pool = self.pool.get("maintenance.project")
        cpi_pool = self.pool.get("cpi.be.entry")
        for project in project_pool.browse(cr, uid, context.get("active_ids"), context):
            if project.date_start and project.cpi_type_id:
                year = datetime.strptime(project.date_start, '%Y-%m-%d').year
                month = datetime.strptime(project.date_start, '%Y-%m-%d').month
                cpi_id = cpi_pool.search(cr, uid, [('type_id','=',project.cpi_type_id.id), ('year','=',year),('month','=',month)], context=context)
                if cpi_id:
                    project_pool.write(cr, uid, project.id, {'initial_cpi_id':cpi_id[0]}, context=context)
        return {'type': 'ir.actions.act_window_close'}
maintenance_project_initial_cpi_id_compute()

class maintenance_project(osv.osv):
    _inherit = 'maintenance.project'
    
    #def _get_contract_file_name(self, cr, uid, ids, field_names, args, context=None):
        #result = {}
        #for project in self.browse(cr, uid, ids, context):
            #result[project.id] = project.code+'.pdf'
        #return result
    
    _columns = {
        'intervention_months' : fields.text("Intervention months"),
        'annual_visits_number' : fields.integer("Number of annual visits"),
                
        'machines' : fields.text("Machines", readonly=False),        
        'nom_visual':fields.char("Nom visual", size=255, readonly=True),
        'entreprise_visual':fields.text("Entreprise visual", readonly=True),
        'client_visual':fields.char("Client visual", size=255, readonly=True),
        'personne_visual':fields.char("Personne visual", size=255, readonly=True),
        
        #disable contract in fields.binary -> performances issues 
        #'contract_file':fields.binary("Contract file (PDF)"),
        #'contract_file_name': fields.function(_get_contract_file_name, type="char", size=255, readonly=True, method=True),
    }
    
    _defaults = {
        #'contract_file_name': 'contract.pdf',
    }
    
    def action_create_update_sale_order(self, cr, uid, ids, context):
        sale_order_pool = self.pool.get("sale.order")
        result = super(maintenance_project, self).action_create_update_sale_order(cr, uid, ids, context)
        for project in self.browse(cr, uid, ids, context):
            sale_order = project.sale_order_id
            if sale_order:
                #find sale_man
                dpt = 10
                shop_id = 1
                sale_man_id = sale_order_pool.find_sale_man_id(cr, uid, sale_order.partner_invoice_id.id, dpt)
                if not sale_man_id:
                    dpt = 11
                    shop_id = 2
                    sale_man_id = sale_order_pool.find_sale_man_id(cr, uid, sale_order.partner_invoice_id.id, dpt)
                sale_order_pool.write(cr, uid, sale_order.id, {'shop_id':shop_id,'user_id':sale_man_id, 'section_id':dpt}, context=context)
                sale_order_pool.order_confirm_elneo(cr, uid, [sale_order.id], context=context)
        return result
    
    def get_sale_order_lines(self, cr, uid, ids, context):
        result = super(maintenance_project, self).get_sale_order_lines(cr, uid, ids, context)
        for project in self.browse(cr, uid, ids, context):
            for line in result:
                line['price_unit'] = project.annual_amount
        return result
    
    def onchange_intervention_delay(self, cr, uid, ids, delay_id, delay_price_included, context=None):
        if delay_id and not delay_price_included:
            return {'value':{'delay_price_init':self.pool.get("maintenance.project.delay").browse(cr, uid, delay_id, context).price}}
        return {}
    
    
maintenance_project()

class maintenance_project_delay(osv.osv):
    _inherit = 'maintenance.project.delay'
    
    _columns = {
        'price':fields.float("Price")
    }
    
maintenance_project_delay()


'''