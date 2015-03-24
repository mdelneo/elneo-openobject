from openerp import models, fields, _, api
from exceptions import Warning
from openerp.tools.safe_eval import safe_eval

'''
from osv import osv, fields
from datetime import datetime
from tools.translate import _ 
import decimal_precision as dp
'''

class purchase_validation_wizard(models.TransientModel):
    _name = 'purchase.validation.wizard'
    _description = 'Purchase validation wizard'
    
    purchase_validation_lines = fields.One2many('purchase.validation.line.wizard','purchase_validation_updater_id','Updated Lines')
    
    @api.model
    def default_get(self,fields):
        """
         To get default values for the object.
         @param fields: List of fields for which we want default values
         @return: A dictionary with default values for all field in ``fields``
        """
        
        
        purchase_validation_lines = []
        
            
        res = super(purchase_validation_wizard, self).default_get(fields)
        
        record_id = self.env.context and self.env.context.get('active_id', False) or False
        purchase = self.env['purchase.order'].browse(record_id)
       
        if purchase:
            for line in purchase.order_line:
                purchase_validation_lines.append({'purchase_line': line.id, 'name':line.name, 'new_price': line.price_unit, 'update_product':True, 'new_date_planned':line.date_planned})                
            if 'purchase_validation_lines' in fields:
                res.update({'purchase_validation_lines': purchase_validation_lines})
                
        return res
    
    def _get_sale_order_lines(self, purchase_validation_line):
        sale_lines = []
        for move in purchase_validation_line.purchase_line.move_ids:
            current_stock_move = move
            while current_stock_move:
                if current_stock_move.sale_line_id:
                    sale_lines.append(current_stock_move.sale_line_id)
                current_stock_move = current_stock_move.move_dest_id
        return sale_lines
    
    @api.model
    def fields_view_get(self,view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(purchase_validation_wizard, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if self.env.context and self.env.context.has_key('step') and self.env.context['step'] == 'warning':
            result['arch'] = '<form string="Warning">'
            
            for message in self.env.context.get('warning_message'):
                result['arch'] += '<label string="%s" colspan="4"/>'%(message.replace("\"", "&quot;"))
                result['arch'] += '<br />'
            result['arch'] += '<button special="cancel" string="Ok" icon="gtk-cancel"/></form>'
            
            
        if self.env.context and self.env.context.has_key('step') and self.env.context['step'] == 'warning_email':
            result['arch'] = '<form string="Warning">'
            
            for message in self.env.context.get('warning_message'):
                result['arch'] += '<label string="%s" colspan="4"/>'%(message.replace("\"", "&quot;"))
                result['arch'] += '<br />'
            result['arch'] += '<button special="cancel" string="Close" icon="gtk-cancel"/><button name="send_mail" type="object" string="Send email" icon="gtk-ok"/></form>'
            
        return result
    
    
    def send_mail(self):
        
        if self.env.context.has_key("order_email"):
            
            email_template = self.browse(safe_eval(self.env['ir.config_parameter'].get_param('purchase_validation.email_template_id','False')))
            
            if not email_template:
                raise Warning(_("No Email Template is defined. Contact your Administrator"))
        
            for order in self.env['sale.order'].browse(self.env.context.get('order_email')):
                order.confirmed_delivery_date = order.delivery_date
                res = self.env['email.template'].generate_email_batch(self,email_template, [order.id],fields=None)
                print res
        
        
        
        '''
        email_template_ids = self.pool.get("email.template").search(cr, uid, [('name','=','Delivery date modification')], context=context)
        if not email_template_ids:
            raise osv.except_osv(_("Error"), _("Impossible to find email template named 'Delivery date modification'. Contact your Administrator"))
        email_template = self.pool.get("email.template").browse(cr, uid, email_template_ids[0], context)
        if context.has_key("order_email"):
            for order in self.pool.get("sale.order").browse(cr, uid, context['order_email']):
                self.pool.get("sale.order").write(cr, uid, [order.id], {'confirmed_delivery_date':order.delivery_date}, context=context)
                mailbox_id = self.pool.get("email.template")._generate_mailbox_item_from_template(cr,uid,email_template,order.id,context=None)
                mailbox = self.pool.get("email_template.mailbox").browse(cr, uid, mailbox_id, context)
                user = self.pool.get("res.users").browse(cr, uid, uid, context)
                account_ids = self.pool.get("email_template.account").search(cr, uid, [('user','=',user.id)], context=context)
                if not user.user_email:
                    raise osv.except_osv(_("Error"), _("Please fill an email for user %s")%(user.name,))
                self.pool.get("email_template.mailbox").write(cr, uid, [mailbox_id], {'folder':'outbox', 'email_from':user.user_email}, context)
                if account_ids:
                    self.pool.get("email_template.mailbox").write(cr, uid, [mailbox_id], {'account_id':account_ids[0]}, context)
        
        return {'type': 'ir.actions.act_window_close'}
    '''
                
                
    @api.one            
    def update_purchase(self):
        # INIT #
        purchase_order_to_update = set()
        
        
        for purchase_validation_line in self.purchase_validation_lines:
            purchase_order_to_update.add(purchase_validation_line.purchase_line.order_id.id)
            
            
            #check if update is needed:
            need_update = True
            supplier_id = purchase_validation_line.purchase_line.order_id.partner_id.id
            for supplierinfo in purchase_validation_line.purchase_line.product_id.product_tmpl_id.seller_ids:
                if supplierinfo.name.id == supplier_id:
                    for pricelist in supplierinfo.displayed_pricelist_ids: #depends technofluid_interne module, else use .pricelist_ids
                        if round(purchase_validation_line.new_price,4) == round(purchase_validation_line.purchase_line.price_unit,4) and\
                            purchase_validation_line.price_quantity == pricelist.min_quantity and \
                            round(purchase_validation_line.new_price,4) == round(pricelist.price,4) and \
                            (not purchase_validation_line.new_discount or round(purchase_validation_line.new_discount,4) == round(pricelist.discount,4)) and \
                            (not purchase_validation_line.new_brut_price or round(purchase_validation_line.new_brut_price,4) == round(pricelist.brut_price,4)):
                            need_update = False
                            break
                if not need_update:
                    break 
        
        
        
        
        
        if warning_message and warning_message != '':
            if delivery_date_changes_email:
                context['step'] = 'warning_email'
            else:
                context['step'] = 'warning'
            context['warning_message'] = warning_message
            return { 
                'view_type' : 'form', 
                'view_mode' : 'form', 
                'res_model' : 'purchase.validation.wizard', 
                'type' : 'ir.actions.act_window', 
                'target' : 'new', 
                'context' : context, 
            } 
        else:
            return {'type': 'ir.actions.act_window_close'}    
            
    '''            
    def update_purchase(self, cr, uid, ids, context=None):
        purchase_validations = self.browse(cr, uid, ids, context)
        purchase_order_line_pool = self.pool.get("purchase.order.line")
        account_invoice_line_pool = self.pool.get("account.invoice.line")
        purchase_order_pool = self.pool.get("purchase.order")
        product_pool = self.pool.get("product.product")
        invoice_line_pool = self.pool.get("account.invoice.line")
        invoice_pool = self.pool.get("account.invoice")
        sale_order_line_pool = self.pool.get("sale.order.line")
        sale_order_pool = self.pool.get("sale.order")
        stock_move_pool = self.pool.get("stock.move")
        stock_picking_pool = self.pool.get("stock.picking")
        sale_order_to_update = set()
        stock_picking_to_update = set()
        purchase_order_to_update = set()
        old_sale_order_delivery_date = {}
        warning_message = []
        
        
        for purchase_validation in purchase_validations:        
            for purchase_validation_line in purchase_validation.purchase_validation_lines:
                sale_lines = None
                
                #update purchase order
                purchase_order_to_update.add(purchase_validation_line.purchase_line.order_id.id)
                
                #check if update is needed:
                need_update = True
                supplier_id = purchase_validation_line.purchase_line.order_id.partner_id.id
                for supplierinfo in purchase_validation_line.purchase_line.product_id.product_tmpl_id.seller_ids:
                    if supplierinfo.name.id == supplier_id:
                        for pricelist in supplierinfo.displayed_pricelist_ids: #depends technofluid_interne module, else use .pricelist_ids
                            if round(purchase_validation_line.new_price,4) == round(purchase_validation_line.purchase_line.price_unit,4) and\
                                purchase_validation_line.price_quantity == pricelist.min_quantity and \
                                round(purchase_validation_line.new_price,4) == round(pricelist.price,4) and \
                                (not purchase_validation_line.new_discount or round(purchase_validation_line.new_discount,4) == round(pricelist.discount,4)) and \
                                (not purchase_validation_line.new_brut_price or round(purchase_validation_line.new_brut_price,4) == round(pricelist.brut_price,4)):
                                need_update = False
                                break
                    if not need_update:
                        break 
                        
                
                #UPDATE PRICE
                if need_update:
                    #Update price in purchase order line
                    purchase_order_line_pool.write(cr, uid, purchase_validation_line.purchase_line.id, {'price_unit':purchase_validation_line.new_price}, context)
                    
                    #Update price in invoice lines
                    #account_invoice_line_pool.write(cr, uid, [invoice_line.id for invoice_line in purchase_validation_line.purchase_line.invoice_lines if invoice_line.invoice_id.state == 'draft'], {'price_unit':purchase_validation_line.new_price}, context)
                    
                    #Update price in product
                    old_supplier_prices = product_pool.update_price_for_supplier(cr, uid, [purchase_validation_line.purchase_line.product_id.id], purchase_validation_line.purchase_line.order_id.partner_id.id, purchase_validation_line.new_price, purchase_validation_line.update_product,purchase_validation_line.new_brut_price,purchase_validation_line.new_discount, purchase_validation_line.price_quantity, ignore_history=(not purchase_validation_line.update_product), context=context)                    
            
                    #Update price on invoice line
                    for purchase_invoice in purchase_validation_line.purchase_line.order_id.invoice_ids:
                        if purchase_invoice.state == 'draft':
                            for purchase_invoice_line in purchase_invoice.invoice_line:
                                if purchase_invoice_line.product_id.id == purchase_validation_line.purchase_line.product_id.id and purchase_invoice_line.quantity == purchase_validation_line.purchase_line.product_qty:
                                    invoice_line_pool.write(cr, uid, purchase_invoice_line.id, {'price_unit':purchase_validation_line.new_price})
                                    invoice_pool.button_reset_taxes(cr, uid, [purchase_invoice.id])
                                
                    #Update sale_order_line
                    sale_order_to_update = set()
                    sale_lines = self._get_sale_order_lines(purchase_validation_line)
                    
                    #compute cost price of sale order
                    for sale_line in sale_lines:
                        sale_order_to_update.add(sale_line.order_id.id)
                        product_cost_price = product_pool._get_cost_price(cr, uid, [sale_line.product_id.id], args={'compute_cost_price':sale_line.product_id.compute_cost_price, 'cost_price_fixed':sale_line.product_id.cost_price_fixed})[sale_line.product_id.id]
                        new_cost_price = sale_order_line_pool.compute_cost_price(cr, uid, ids, sale_line.product_id.id, sale_line.order_id.partner_id.id, product_cost_price)
                        sale_order_line_pool.write(cr, uid, [sale_line.id], {"purchase_price":new_cost_price})
                        for invoice_line in sale_line.invoice_lines:
                            self.pool.get("account.invoice.line").write(cr, uid, [invoice_line.id], {"cost_price":new_cost_price})
                    
                    #reset old product supplier price
                    if not purchase_validation_line.update_product and old_supplier_prices:
                        product_pool.update_price_for_supplier(cr, uid, [purchase_validation_line.purchase_line.product_id.id], purchase_validation_line.purchase_line.order_id.partner_id.id, old_supplier_prices[purchase_validation_line.purchase_line.product_id.id][0], purchase_validation_line.update_product, old_supplier_prices[purchase_validation_line.purchase_line.product_id.id][1],old_supplier_prices[purchase_validation_line.purchase_line.product_id.id][2], old_supplier_prices[purchase_validation_line.purchase_line.product_id.id][3], ignore_history=True, context=context)
                    else:
                        warning_message.append(_("Product '%s' price has been updated from %s to %s.")%(purchase_validation_line.purchase_line.product_id.name, old_supplier_prices[purchase_validation_line.purchase_line.product_id.id] and old_supplier_prices[purchase_validation_line.purchase_line.product_id.id][0] or '0', purchase_validation_line.new_price))
                
                #UPDATE DATE
                if purchase_validation_line.new_date_planned != purchase_validation_line.purchase_line.date_planned:
                    #compute difference between new date_planned and old date_planned
                    difference = datetime.strptime(purchase_validation_line.new_date_planned, '%Y-%m-%d') - datetime.strptime(purchase_validation_line.purchase_line.date_planned, '%Y-%m-%d')
                    
                    #Update purchase_order_line
                    purchase_order_line_pool.write(cr, uid, purchase_validation_line.purchase_line.id, {'date_planned':purchase_validation_line.new_date_planned}, context)
                    
                    #Update reception
                    stock_move_ids = stock_move_pool.search(cr, uid, [('purchase_line_id', '=', purchase_validation_line.purchase_line.id)], context=context)
                    stock_moves = stock_move_pool.browse(cr, uid, stock_move_ids, context)
                    stock_picking_to_update.update([stock_move.picking_id.id for stock_move in stock_moves])
                    stock_move_pool.write(cr, uid, stock_move_ids, {'date_expected':purchase_validation_line.new_date_planned})
                    
                    #update sale_order_line delay
                    if not sale_lines:
                        sale_lines = self._get_sale_order_lines(purchase_validation_line)
                    for sale_line in sale_lines:                        
                        sale_order_line_pool.write(cr, uid, [sale_line.id for sale_line in sale_lines], {'delay':sale_line.delay + difference.days}, context = context)
                        sale_order_to_update.add(sale_line.order_id.id)
                        old_sale_order_delivery_date[sale_line.order_id.id] = sale_line.order_id.delivery_date
                        
                    #update delivery
                    for move in stock_moves:
                        current_stock_move = move
                        while current_stock_move:
                            if current_stock_move.picking_id.type == 'out':
                                new_date = datetime.strptime(current_stock_move.date_expected, '%Y-%m-%d %H:%M:%S') + difference
                                stock_move_pool.write(cr, uid, current_stock_move.id, {'date_expected':new_date.strftime('%Y-%m-%d %H:%M:%S'),'date':new_date.strftime('%Y-%m-%d %H:%M:%S')})
                                stock_picking_to_update.add(current_stock_move.picking_id.id)
                            current_stock_move = current_stock_move.move_dest_id
                
        if sale_order_to_update:
            sale_order_pool.button_dummy(cr, uid, list(sale_order_to_update), context)
        if stock_picking_to_update:    
            stock_picking_pool.write(cr, uid, list(stock_picking_to_update), {})
        if purchase_order_to_update:
            purchase_order_pool.write(cr, uid, list(purchase_order_to_update), {'validated':True})
            
        #check sale_order delivery date update :
        delivery_date_changes_email = []
        delivery_date_changes_noemail = []
        for sale_order in sale_order_pool.browse(cr, uid, old_sale_order_delivery_date.keys(), context=context):
            if sale_order.delivery_date and datetime.strptime(sale_order.delivery_date, '%Y-%m-%d') > datetime.strptime(old_sale_order_delivery_date[sale_order.id], '%Y-%m-%d'):
                date_from_string = datetime.strptime(old_sale_order_delivery_date[sale_order.id], '%Y-%m-%d').strftime('%d/%m/%Y')
                date_to_string = datetime.strptime(sale_order.delivery_date, '%Y-%m-%d').strftime('%d/%m/%Y')
                warning_message.append(_("Delivery date of the sale order %s was postponed from %s to %s.")%(sale_order.name, date_from_string, date_to_string))
            if sale_order.confirmed_delivery_date and datetime.strptime(sale_order.confirmed_delivery_date, '%Y-%m-%d') < datetime.strptime(sale_order.delivery_date, '%Y-%m-%d'):
                confirmed_delivery_date = datetime.strptime(sale_order.confirmed_delivery_date, '%Y-%m-%d').strftime('%d/%m/%Y')
                warning_message.append(_("Delivery date confirmed to the customer (%s) for order %s is no longer correct.")%(confirmed_delivery_date, sale_order.name))
                if sale_order.partner_order_id and sale_order.partner_order_id.email: 
                    delivery_date_changes_email.append(sale_order)
                else:
                    delivery_date_changes_noemail.append(sale_order)
            
            if delivery_date_changes_noemail:
                warning_message.append(_('Some of customer have a delivery date that has changed, but order address has no email :\r\n'))
                for sale_order in delivery_date_changes_email:
                    warning_message.append('  - '+sale_order.partner_id.name+' - '+sale_order.name+' - '+datetime.strptime(sale_order.delivery_date, '%Y-%m-%d').strftime('%d/%m/%Y')+'\r\n')
            
            if delivery_date_changes_email:
                context['order_email'] = []
                warning_message.append(_('Do you want send an email to following customers about theses modifications :')+'\r\n')
                for sale_order in delivery_date_changes_email:
                    warning_message.append('  - '+sale_order.partner_id.name+' - '+sale_order.name+' - '+datetime.strptime(sale_order.delivery_date, '%Y-%m-%d').strftime('%d/%m/%Y')+' - '+sale_order.partner_order_id.email+'\r\n')
                    context['order_email'].append(sale_order.id)                    
        
        if warning_message and warning_message != '':
            if delivery_date_changes_email:
                context['step'] = 'warning_email'
            else:
                context['step'] = 'warning'
            context['warning_message'] = warning_message
            return { 
                'view_type' : 'form', 
                'view_mode' : 'form', 
                'res_model' : 'purchase.validation.wizard', 
                'type' : 'ir.actions.act_window', 
                'target' : 'new', 
                'context' : context, 
            } 
        else:
            return {'type': 'ir.actions.act_window_close'}
    '''
purchase_validation_wizard()

class purchase_validation_line_wizard(models.TransientModel):
    
    _name = 'purchase.validation.line.wizard'
    _description = 'Purchase updater line wizard'
 
    purchase_validation_updater_id = fields.Many2one('purchase.validation.wizard','Purchase Validation Wizard')
    purchase_line = fields.Many2one('purchase.order.line','Purchase Order Line')
    name = fields.Char('Name',size=64,readonly=True)
    update_product=fields.Boolean("Update Product Price ?")
    new_price = fields.Float("New Price",digits=(20,6))
    new_date_planned=fields.Date("Scheduled Date",select=True)
    new_brut_price=fields.Float("New Brut Price",digits=(20,6))
    new_discount=fields.Float("New Discount")
    price_quantity=fields.Float("Quantity",default=1)
 
    
purchase_validation_line_wizard()