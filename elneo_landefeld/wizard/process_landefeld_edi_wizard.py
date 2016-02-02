
from openerp import models, fields, api, _, SUPERUSER_ID

import base64


class EDIProcessorLandefeld(models.TransientModel):
    _name='edi.processor.landefeld'
    
    TYPE_NONE = 0
    TYPE_TELEPHONE = 1
    TYPE_FAX = 2
    TYPE_MAIL=3
    TYPE_LANDEFELD=4
    TYPE_SHOP=8
    TYPE_OPENTRANS=9
    
    edi_message = fields.Many2one('edi.message',string='Edi Message',required=True)
    edi_processor = fields.Many2one('edi.processor',string='EDI Processor',required=True)
    
    warning_message = fields.Text('Warning Message',default='')
    error_message = fields.Text('Error Message',default='')
    
    state = fields.Selection([('draft','Draft'),('ok','OK'),('warning','Warning'),('error','Error')],default='draft')
    
    
    @api.multi
    def write(self,vals):
        if vals.has_key('warning_message') and vals['warning_message']:
            vals.update({'state':'warning'})
            
        if vals.has_key('error_message') and vals['error_message']:
            vals.update({'state':'error'})
    
        super(EDIProcessorLandefeld,self).write(vals)
    
    @api.model
    def get_control_type(self,control_info):
        control_type = self.TYPE_NONE
        if control_info.generator_info:
            type_num = int(control_info.generator_info[0])
            if type_num == 1:
                control_type = self.TYPE_TELEPHONE
            if type_num == 2:
                control_type = self.TYPE_FAX
            if type_num == 3:
                control_type = self.TYPE_MAIL
            if type_num == 4:
                control_type = self.TYPE_LANDEFELD
            if type_num == 8:
                control_type = self.TYPE_SHOP
            if type_num == 9:
                control_type = self.TYPE_OPENTRANS
                            
        return control_type
    
    @api.model
    def _search_order_ids_byref(self,supplier_order_id=None,order_id=None):
        res = []
        
        purchase_order_ids = None
        
        if supplier_order_id:
            supplier_order_id = supplier_order_id
        else:
            supplier_order_id = False
        
        
        
        
        ''' NEVER USED IN ORDERRESPONSE...
        # from dispatch_note
        if (xml.has_key('lines') and xml['lines'][0].has_key('order_id')):
            order_id = xml['lines'][0]['order_id']
            if xml['lines'][0].has_key('supplier_order_id'):
                supplier_order_id = xml['lines'][0]['supplier_order_id']
        elif (xml.has_key('order_id')):
            order_id = xml['order_id']
            
        '''
        
        order_id = order_id
                    
        if order_id:
            order_id = order_id.split("//")[0] #order id can be followed by customer purchase number (after '//')
        '''
        req_purchase_search = []
        if supplier_order_id and order_id:
            req_purchase_search = ['|',('landefeld_customer_ref','=',order_id),('landefeld_ref','=',supplier_order_id)]
        elif supplier_order_id:
            req_purchase_search = [('landefeld_ref','=',supplier_order_id)]
        
        '''
        if order_id:
            req_purchase_search = [('landefeld_customer_ref','=',order_id)]
        elif supplier_order_id:
            req_purchase_search = [('landefeld_ref','=',supplier_order_id)]
        
        
        
        #in order_id field, our reference can be followed by customer purchase reference (after '//')
        purchase_order_ref = order_id
        
        
        # 1 - Simple search
        if purchase_order_ref:
            purchase_order_ids = self.env['purchase.order'].search([('name','ilike',purchase_order_ref)])
            if len(purchase_order_ids) > 0:
                purchase_order_ids = self.env['purchase.order'].search([('name','=',purchase_order_ref)])
        
        # 2 - Search on order reference
        if not purchase_order_ids and purchase_order_ref:
            if len(purchase_order_ref) == 14 and (purchase_order_ref[4:7] == '-A-' or purchase_order_ref[4:7] == '-W-'):
                purchase_order_ids = self.env['purchase.order'].search([('name','=',purchase_order_ref[7:])])
                if purchase_order_ids:
                    self.edi_processor.edi_log('info',_('Purchase order found with criteria %s:%s') % (purchase_order_ref,unicode(purchase_order_ids[0])))
                    return purchase_order_ids
                
        # 3 - Search on landefeld ref
        if not purchase_order_ids and supplier_order_id:
            #first : search only with landefeld ref
            purchase_order_ids = self.env['purchase.order'].search( [('landefeld_ref','=',supplier_order_id)])
            if not purchase_order_ids:
                purchase_order_ids = self.env['purchase.order'].search(req_purchase_search)
            if purchase_order_ids:
                self.edi_processor.edi_log('info',_('Purchase order found with criteria %s') % (map(str,req_purchase_search)))
                return purchase_order_ids
            
        if not purchase_order_ids:
            if purchase_order_ref:
                obj_seqs = self.env['ir.sequence'].search([('code','=','purchase.order')])
                
                for obj_seq in obj_seqs:
                    start = purchase_order_ref.find(obj_seq.prefix)
                    end = start + ((obj_seq.prefix and len(obj_seq.prefix)) or 0) + obj_seq.padding + ((obj_seq.suffix and len(obj_seq.suffix)) or 0)
                    if start != -1 and len(purchase_order_ref) >= end: 
                        search_string = purchase_order_ref[start:end]
                        purchase_order_ids = self.env['purchase.order'].search([('name','like',search_string)])
                        if purchase_order_ids:
                            self.edi_processor.edi_log('info',_('Purchase order found with name like %s') % search_string)
                        else:
                            return res
                    else: 
                        return res       
            else:
                return res             
        
            
            
        res = purchase_order_ids    
        
        return res
    
    @api.model
    def get_address(self,data, partner_id, address_type):
        address_pool = self.env['res.partner']
        address_ids = address_pool.search([('landefeld_ref','=',data['landefeld_partner_id'])])
        if not address_ids:
            address_ids = address_pool.search([('parent_id','=',partner_id),('type','=',address_type),('name','=',data['name']),('street','=',data['street']),('zip','=',data['zip']),('city','=',data['city'])])
            if address_ids:
                #UPDATE the address with the landefeld ref
                address_pool.write([address_ids[0]],{'landefeld_ref':data['landefeld_partner_id']})
                
        if address_ids:
            return address_ids[0]
        #address not found : create it
        #find country
        address_data = {
            'parent_id':partner_id, 
            'type':address_type, 
            'name':data['name'],
            'street':data['street'], 
            'zip':data['zip'], 
            'city':data['city'], 
            'landefeld_ref':data['landefeld_partner_id']
        }
        country_ids = self.env['res.country'].search([('code','=',data['country_code'])])
        if country_ids:
            address_data['country_id'] = country_ids[0].id
            
                        
        return address_pool.create(address_data)
    
    @api.model
    def get_remarks_detail(self,document):
        client_id=None
        buyer=None
        email=None
        note=None
        for remark in document.element.order_response_header.order_response_info.remarks:
            if len(remark) > 0 and remark.find("Kundennummer:") > -1:
                client_id=remark[14:len(remark)].strip()
            elif len(remark) > 0 and remark.find("Besteller:") > -1:
                buyer=remark[11:len(remark)].strip()
            elif len(remark) > 0 and remark.find("Besteller-Email:") > -1:
                email=remark[17:len(remark)].strip()
            else :
                note += '\n' + remark
        
        return client_id,buyer,email,note
    
    @api.model
    def _get_prices(self,item):
        discount_relative=0
        discount_absolute=0
        sale_unit_price = 0
        sale_discount=0
        price_amount=0
        price_unit=0
        price_quantity=0
        
        if item.product_price_fix is not None:
            
            
            try:
                price_amount=float(item.product_price_fix.price_amount.replace(',','.'))
                price_quantity=float(item.product_price_fix.price_quantity.replace(',','.'))
                price_unit=price_amount/price_quantity
            except Exception, e:
                raise Exception('Error when calculating order item price unit : '+unicode(e))
            
            for aoc in item.product_price_fix.allow_or_charge_fix.allow_or_charge:
                if aoc.charge_type is not None and aoc.charge_type =='rebate':
                    if aoc.charge_value.percentage_factor:
                        discount_relative = float(aoc.charge_value.percentage_factor)
                        discount_absolute += -((price_amount/price_quantity)*discount_relative)
            
            #discount_absolute = -((price_amount/price_quantity)*discount_relative)
            if (price_amount != 0 or price_quantity != 0) and (price_amount/price_quantity) !=0:
                discount_relative = (((price_amount/price_quantity)-discount_absolute)/(price_amount/price_quantity))/100
            if item.shop_price_amount is not None:
                sale_unit_price = float(item.shop_price_amount)
                sale_discount = float(item.shop_rebate_factor)
            
        return{
               'discount_relative' : discount_relative,
               'discount_absolute' : discount_absolute,
               'sale_unit_price' : sale_unit_price,
               'sale_discount' : sale_discount,
               'price_amount' : price_amount,
               'price_unit' : price_unit,
               'price_quantity' : price_quantity
               }
    
    
    def _get_item_sequence(self,item):
        sequence=10
        try:
            if item.line_item_id.isdigit():
                sequence =  int(item.line_item_id)
        except Exception,e:
            raise Exception('Error when parsing item "sequence" : '+unicode(e))
        
        return sequence
    
    def _is_item_service(self,item):
        if item.product_id.supplier_pid and item.product_id.supplier_pid.strip()[0] == '_':
            return True
        else:
            return False
    
    def _get_item_route(self,route_type='drop'):
        res = None
        if route_type=='drop':
            route_drop_landefeld = self.env['stock.location.route'].search([('landefeld_dropship','=',True)],limit=1)
            if route_drop_landefeld:
                return route_drop_landefeld.id
            else:
                route_drop = self.env['stock.location.route'].search([('pull_ids.location_id.usage','=','customer'),('pull_ids.action','=','buy')],limit=1)
                return route_drop.id
        return res
    
    @api.one
    def _process_purchase_from_response(self,document,purchase_order=None,sale_order=None):
               
        #Validate purchase order prices and delay
        if not sale_order and not purchase_order: #if we haven't sale order id and purchase order id, anything goes wrong
            self.edi_message.state = 'error'
            #('Error sale order or purchase order not found') 
        else:
            
            #Get purchase order
            try:
                if not purchase_order:
                    if sale_order.purchase_ids:
                        purchase_order = sale_order.purchase_ids[0]
                        purchase_order.landefeld_internet_purchase = True
                        purchase_order.partner_ref = document.element.order_response_header.order_response_info.supplier_order_id
                        purchase_order.landefeld_ref = document.element.order_response_header.order_response_info.supplier_order_id
                        purchase_order.landefeld_customer_ref = document.element.order_response_header.order_response_info.order_id
                        purchase_order.invoice_method = 'order'
                    
                    
                purchase_order.signal_workflow('purchase_confirm')
                
                new_purchase_validation_lines = []
                
                #index product_ids of xml lines
                products=self.env['product.product']
                for item in document.element.item_list.order_items:
                    products_found = self.env['product.product'].findByCode(item.product_id.supplier_pid)
                    products += products_found
                    
                    #check if all purchase order lines are validated by order response
                    found = False
                    for product_found in products_found:
                        if product_found in purchase_order.order_line.mapped('product_id'):
                            found = True
                            continue
                    if not found :
                        self.state = 'warning'
                        self.warning_message += _('Error when importing Landefeld order confirmation of %s : product %s is not in order confirmation.')%(purchase_order.name, unicode(item.product_id.supplier_pid))
                        self.warning_message += '\n'

                    purchase_line_id = None
                    if not products_found:
                        self.warning_message += '\n WARNING : No product found for product code : "'+item.product_id.supplier_pid+'"'
                    else:
                        
                        purchase_line = self.env['purchase.order.line'].findPurchaseLineByProduct(purchase_order, products_found)
                        if purchase_line :
                            purchase_line_id = purchase_line.id
                        if not purchase_line_id:
                            self.warning_message += '\n WARNING : No purchase line found for product code : "'+item.product_id.supplier_pid+'"'
                    if purchase_line:
                        if self._is_item_service(item):
                            update_product=False
                        else:
                            update_product = True
                            
                        prices = self._get_prices(item)
                          
                        #if absolute discount not specified : compute it from relative discount
                        if not prices['discount_absolute'] and prices['discount_relative'] and prices['price_unit']:
                            prices['discount_absolute'] = (1-prices['discount_relative'])*prices['price_unit']
                            
                        #if detail (discount, ...) of price is not specified, don't update price 
                        new_purchase_validation_lines.append((0,0,{
                                        'price_quantity':prices["price_quantity"], 
                                        'purchase_line':purchase_line.id,
                                        'update_product':update_product,
                                        'new_price':prices['price_unit']+(prices['discount_absolute']),
                                        'new_brut_price':prices['price_unit'], 
                                        'new_discount':prices['discount_relative']*100,  
                                        'new_date_planned':document.element.order_response_header.order_response_info.delivery_date.delivery_end_date or None
                        }))
                    elif not item.product_id.supplier_pid or not self._is_item_service(item):
                        self.state = 'warning'
                        self.warning_message += _('Error when importing Landefeld order response of %s : the product code %s is not found. Please check it.')%(purchase_order.name, item.product_id.supplier_pid)
                        self.warning_message += '\n'
                        
                        
                
                
                purchase_validation_id = self.env['purchase.validation.wizard'].create({
                        'purchase_validation_lines':new_purchase_validation_lines
                })
                    
                purchase_validation_id.update_purchase()
            except Exception,e:
                self.error_message += '\n Warning : error when validate purchase "lines" : '+unicode(e)+'\n'
                
                
        if purchase_order:
            purchase_order.landefeld_orderresponse_received = True
            
            if self.warning_message :
                
                if purchase_order.validator and purchase_order.validator.partner_id.email:
                    if self.TYPE_OPENTRANS == self.get_control_type(document.element.order_response_header.control_info):
                        self.send_warning_email(purchase_order.validator.partner_id.email, _("OpenTrans Landefeld : Warning when validate order confirmation"), self.warning_message, notify_other=False)
                        
                        
    def send_warning_email(self,email_address, email_subject, email_message, notify_other):
        if self.edi_message.warning_report_sent:
            return
        
        mail={
              'email_from':self.env['res.users'].browse(SUPERUSER_ID).partner_id.email,
              'email_to':self.edi_message.type.processor.send_warning_users.mapped('partner_id.email'),
              'subject':email_subject,
              'body_text':email_message,
              'account_id':SUPERUSER_ID,
              'res_id':self.edi_message.id,
              'model':'edi.message',
              
              }
        
        self.env['mail.message'].create(mail)
        self.edi_message.warning_report_sent=True
        
        return True
    
    @api.one
    def _process_order_response(self,document):
        origin = ''
        if self.get_control_type(document.element.order_response_header.control_info) == self.TYPE_SHOP:
            if document.element.order_response_header.order_response_info.supplier_order_id:
                origin = origin + document.element.order_response_header.order_response_info.supplier_order_id + ' '
            else:
                self.warning_message='Supplier order id is not defined on OpenTrans document'
                
        purchase_order = self.env['purchase.order']
        sale_order = self.env['sale.order']
        
        if self.get_control_type(document.element.order_response_header.control_info) != self.TYPE_SHOP:
            #IT S NOT A SHOP ORDER
            purchase_order_ids=None
            #purchase_order_ref = document.element.order_response_header.order_response_info.order_id.split('//')[0]
            
            if self.get_control_type(document.element.order_response_header.control_info) != self.TYPE_NONE:
                purchase_orders = self._search_order_ids_byref(document.element.order_response_header.order_response_info.supplier_order_id,document.element.order_response_header.order_response_info.order_id)
                
            if purchase_orders:
                purchase_order = purchase_orders[0]
                sale_order_id = self.env['sale.order'].find_by_purchase_order(purchase_order)
                if sale_order_id:
                    self.edi_processor.edi_log('info',_('Sale order found : %s' % unicode(sale_order_id)))
                    
        else:                             
            #INTERNET SALE : create new sale order                                                  
            self.edi_processor.edi_log('info',_('Internet sale order behavior'))
            
            landefeld_id = None
            for party in document.element.order_response_header.order_response_info.parties.parties:
                if party.party_role == 'delivery':
                    delivery_party=party
                    
            
            #Search res_partner
            account_ids = self.env['elneo.webshop.account'].search(['|',('login','=',document.element.order_response_header.order_response_info.customer_no),('landefeld_id','=',delivery_party.party_id)])
            
            if len(account_ids) <= 0:
                self.edi_processor.edi_log('info',_('No account found with login : %s or with id %s' % (document.element.order_response_header.order_response_info.customer_no,delivery_party.party_id)))
            else:
                account = account_ids[0]
                partner = account.partner_id
                #shop_id = shop_ids[0]
                
                address_data = {
                                'country_code':delivery_party.address.country_coded, 
                                'name':delivery_party.address.name,
                                'landefeld_partner_id':delivery_party.party_id,
                                'street':delivery_party.address.street,
                                'city':delivery_party.address.city,
                                'zip':delivery_party.address.zip,
                                }
                
                addr_delivery_id = self.get_address(address_data, partner.id, 'delivery')
                addr_order_id = None
                
                
                #GET client_id, buyer, email
                client_id, buyer, email, note = self.get_remarks_detail(document)
                
                if email is None and account.email:
                    email=account.email
                    
                if email:
                    addr_order_ids = self.env['res.partner'].search([('parent_id','=',partner.id), ('email','=',email), ('type','in',['contact','default'])])
                    if addr_order_ids:
                        addr_order_id = addr_order_ids[0]
                    else:
                        addr_delivery_id.write({'email':email})
                if not addr_order_id:
                    addr_order_id = addr_delivery_id
                    
                #use invoice address of customer if only one address exists, else use order address
                addr_invoice_ids = self.env['res.partner'].search([('parent_id','=',partner.id),('type','=','invoice')])
                if len(addr_invoice_ids) == 1:
                    addr_invoice_id = addr_invoice_ids[0]
                else:
                    addr_invoice_id = addr_order_id
                
                #find seller
                section_id = 7
                seller_id = self.env['sale.order']._find_sale_man_id(addr_delivery_id.id,section_id=section_id)
                if not seller_id:
                    section_id = 8
                    seller_id = self.env['sale.order']._find_sale_man_id(addr_delivery_id.id,section_id=section_id)
                    
                sale_orders = self.env['sale.order'].search([('landefeld_ref','=',document.element.order_response_header.order_response_info.supplier_order_id)])
                if sale_orders and len(sale_orders) == 1:
                    self.edi_processor.edi_log('info','Sale order already exists (id : %s)' % unicode(sale_orders.id))
                elif sale_orders and len(sale_orders) > 1:
                    error_msg = 'Sale order already exists, and several sales found ('+str(sale_orders.mapped('id'))+')'
                    self.edi_processor.edi_log('error', + error_msg)
                    raise Exception(error_msg)
                else:
                    #Save sale_order
                    sale_order = self.env['sale.order'].create({
                                                                             'date_confirm': document.element.order_response_header.order_response_info.order_response_date,
                                                                             'confirmed_delivery_date': document.element.order_response_header.order_response_info.delivery_date.delivery_end_date,
                                                                              'picking_policy':'one',
                                                                              #'picking_policy':'direct',
                                                                              #'order_policy':'postpaid',
                                                                              'order_policy':'picking',
                                                                              'shop_sale':False,
                                                                              'target_invoiced_rate':0,
                                                                              'target_invoiced_amount':0,
                                                                              'date_order':document.element.order_response_header.control_info.generation_date, 
                                                                              'partner_id':partner.id,
                                                                              'carrier_id':1,
                                                                              'pricelist_id': partner.property_product_pricelist.id,
                                                                              'partner_order_id': addr_order_id.id,
                                                                              'quotation_address_id':addr_order_id.id,
                                                                              'partner_invoice_id': addr_invoice_id.id,
                                                                              'partner_shipping_id': addr_delivery_id.id, 
                                                                              'landefeld_internet_sale':True, 
                                                                              'landefeld_automatic_purchase':False,
                                                                              'landefeld_ref':document.element.order_response_header.order_response_info.supplier_order_id, 
                                                                              'client_order_ref':document.element.order_response_header.order_response_info.order_id, 
                                                                              'user_id':seller_id, 
                                                                              'section_id':section_id,
                                                                              'payment_term': partner.property_payment_term.id,
                                                                              'discount_type_id':partner.discount_type_id.id,
                                                                              'fiscal_position':partner.property_account_position.id,
                                                                              'note':note,                                               
                                                                             })
                    print sale_order.id
                    
                    for item in document.element.item_list.order_items:
                        
                        prices = self._get_prices(item)
                        
                        #xml['lines'] = self.compute_landefeld_cost(xml['lines'])
                        
                        product = self.env['product.product'].findOrCreateProduct(
                                                              item.product_id.supplier_pid, 
                                                              prices['price_unit'], 
                                                              prices['discount_absolute'], 
                                                              prices['discount_relative'], 
                                                              item.product_id.description_short)
                        #check if Landefeld is a supplier for the product
                        landefeld_found = False 
                        for supplierinfo in product.seller_ids:
                            if supplierinfo.name.id == self.env['product.product'].LANDEFELD_PARTNER_ID:
                                landefeld_found = True
                        if not landefeld_found:
                            raise Exception('Landefeld is not supplier for product "'+item.product_id.supplier_pid+'" (id : '+unicode(product.id)+')')
                        
                      
                        #Save sale_order_line
                
                        new_order_line = self.env['sale.order.line'].with_context(supplier_id=self.env['product.product'].LANDEFELD_PARTNER_ID).product_id_change(
                        sale_order.pricelist_id.id, product.id, qty=float(item.quantity), 
                        partner_id=partner.id, lang=partner.lang, fiscal_position=sale_order.fiscal_position.id, update_tax=True)['value']
                        
                        new_order_line['tax_id'] = [(4,tax_id) for tax_id in new_order_line['tax_id']]
                            
                        new_order_line.update({
                              'order_id': sale_order.id, 
                              'product_id':product.id,
                              'route_id' : self._get_item_route('drop'),
                              #'type':'make_to_order',
                              'state':'draft',
                              'sequence': self._get_item_sequence(item), 
                              'price_unit': prices['sale_unit_price'],
                              'discount': prices['sale_discount'],
                              'product_uom': product.uom_id and product.uom_id.id or 1,
                              'product_uom_qty': float(item.quantity)})
                        
                        #if xml_line.has_key('update_purchase_price') and xml_line['update_purchase_price']:
                        if not prices['discount_absolute'] and prices['discount_relative'] and prices['price_unit']:
                            prices['discount_absolute'] = (1-prices['discount_relative'])*prices['price_unit']
                            
                        new_order_line.update({
                              'purchase_price': prices['price_unit']+(prices['discount_absolute']), })
                        
                        #if not xml_line.has_key('in_purchase_only') or xml_line['in_purchase_only'] == False:
                            #self.pool.get('sale.order.line').create(cr, uid, new_order_line)
                        self.env['sale.order.line'].create(new_order_line) 
                    
                    #validate sale order
                    sale_order.signal_workflow('order_confirm')
                    #wf_service.trg_validate(uid, 'sale.order', sale_order_id, 'order_confirm', cr)
                    
                    #force availability of delivery order
                    sale_order.picking_ids.force_assign()
                    #self.pool.get("stock.picking").force_assign(cr, uid, [pick.id for pick in sale_order.picking_ids])
            
            
        if purchase_order:
            origin = origin + purchase_order.name+' '
        if sale_order.landefeld_automatic_sale or sale_order.landefeld_internet_sale:
            origin = origin + sale_order.name+' '    
            
        self._process_purchase_from_response(document,purchase_order, sale_order)
        
        
        if self.state=='draft':
            self.state='ok'
            
    def _check_parties_delivery(self,parties):
        for party in parties:
            if party.party_role == 'delivery':
                return True
        
        return False
        
    def _get_party_delivery(self,parties):
        for party in parties:
            if party.party_role == 'delivery':
                return party
            
            
    def _do_delivery(self,document,out_pickings):
        
        items = document.element.item_list.items
        
        
        
        partial_data = {'items':[],
            'delivery_date':document.element.header.control_info.generation_date
            }
        
        stock_moves_ok = self.env['stock.move']
        for item in items:
        
            if float(item.quantity) > 0 :
                products = self.env['product.product'].findByCode(item.product_id.supplier_pid)
                
                if not products:
                    self.warning_message+=_("Error when validating dispatch note from Landefeld : Product %s not found in database.")%(item.product_id.supplier_pid)
                    return False
                
                stock_moves = self.env['stock.move'].search([('product_id','=',products.mapped('id')),('picking_id','in',out_pickings.mapped('id'))])
                
                stock_moves_tmp = stock_moves.filtered(lambda r:r not in stock_moves_ok)
                
                if not stock_moves_tmp:
                    self.warning_message += _("Error when validating dispatch note from Landefeld : Product %s not found in delivery picking %s.")%(item.product_id.supplier_pid,out_pickings.mapped('name'))
                    self.warning_message += '\n'
                    return False
                
                elif len(stock_moves_tmp) > 1:
                    stock_move_id = None
                    alternative_stock_move_id = None
                    
                    for stock_move in stock_moves_tmp:
                        if float(item.quantity) == stock_move.product_qty:
                            stock_move_id = stock_move.id
                        if float(item.quantity) < stock_move.product_qty:
                            alternative_stock_move_id = stock_move.id
                    if not stock_move_id:
                        stock_move_id = alternative_stock_move_id
                    if not stock_move_id:                    
                        self.warning_message +=  _("Error when validating dispatch note from Landefeld : No product %s found in delivery picking %s for quantity %s.")%(item.product_id.supplier_pid,out_pickings.mapped('name'), unicode(item.quantity))
                        self.warning_message += '\n'
                        return False
                    
                else:
                    stock_move_id = stock_moves_tmp[0]
                    
                stock_moves_ok += stock_move_id
                    
                product = stock_move_id.product_id
                partial_data['items'].append({'prodlot_id': False, 'product_id': product.id, 'product_uom': 1, 'product_qty': float(item.quantity)})
                #partial_data.update({'move'+unicode(stock_move_id.id):{'prodlot_id': False, 'product_id': product.id, 'product_uom': 1, 'product_qty': float(item.quantity)}})
        
        
        transfer = self.env['stock.transfer_details'].with_context(active_ids=out_pickings.mapped('id'),active_model='stock.picking').create({})
        
        self._do_prepare_transfer(out_pickings, transfer,partial_data)
        
        transfer.with_context(active_ids=out_pickings.mapped('id'),active_model='stock.picking').do_detailed_transfer()
        
        #delivered_pack_id = out_pickings.do_partial(partial_data)
        
        return True
    
    def _do_prepare_transfer(self,picking,transfer, partial_data):
        picking.ensure_one()
        transfer.picking_id = picking
        if not picking.pack_operation_ids:
            picking.do_prepare_partial()
        for partial in partial_data['items']:
            for op in picking.pack_operation_ids:
                if partial['product_id'] and partial['product_id'] == op.product_id.id:
                    item = {
                        'packop_id': op.id,
                        'product_id': op.product_id.id,
                        'product_uom_id': partial['product_uom'],
                        'quantity': partial['product_qty'],
                        'package_id': op.package_id.id,
                        'lot_id': op.lot_id.id,
                        'sourceloc_id': op.location_id.id,
                        'destinationloc_id': op.location_dest_id.id,
                        'result_package_id': op.result_package_id.id,
                        'date': op.date, 
                        'owner_id': op.owner_id.id,
                        'transfer_id':transfer.id
                    }
            
            if op.product_id:
                self.env['stock.transfer_details_items'].create(item)
                #transfer.item_ids+=item
            elif op.package_id:
                self.pack_operation_ids.append(item)
        '''
        
        stock_move_ids_ok = []
        for line in xml['lines']:
            
            if float(line['quantity']) > 0:
                product_ids = self.pool.get("product.product").findByCode(cr, uid, line['product_supplier_code'], context)
            
                if not product_ids:
                    warning_message = _("Error when validating dispatch note from Landefeld : Product %s not found in database.")%(line['product_supplier_code'],)
                    warning_mail = warning_mail + warning_message + '\n'
                    raise Exception("Product "+line['product_supplier_code']+" not found in database")
                
                stock_move_ids = self.pool.get("stock.move").search(cr, uid, [('product_id','in',product_ids), ('picking_id','=',delivery_order.id)])
                stock_move_ids = [m for m in stock_move_ids if (m not in stock_move_ids_ok)]
            
                if not stock_move_ids:
                    warning_mail = warning_mail + _("Error when validating dispatch note from Landefeld : Product %s not found in delivery picking %s.")%(line['product_supplier_code'],delivery_order.name)
                    warning_mail = warning_mail + '\n'
                    raise Exception("Product "+line['product_supplier_code']+" not found in "+delivery_order.name)
                elif len(stock_move_ids) > 1:
                    stock_move_id = None
                    alternative_stock_move_id = None
                    for stock_move in self.pool.get("stock.move").browse(cr, uid, stock_move_ids, context):
                        if float(line['quantity']) == stock_move.product_qty:
                            stock_move_id = stock_move.id
                        if float(line['quantity']) < stock_move.product_qty:
                            alternative_stock_move_id = stock_move.id
                    if not stock_move_id:
                        stock_move_id = alternative_stock_move_id
                    if not stock_move_id:                    
                        warning_mail = warning_mail + _("Error when validating dispatch note from Landefeld : No product %s found in delivery picking %s for quantity %s.")%(line['product_supplier_code'],delivery_order.name, unicode(line['quantity']))
                        warning_mail = warning_mail + '\n'
                        raise Exception("Several products "+line['product_supplier_code']+" found in "+delivery_order.name)
                else:
                    stock_move_id = stock_move_ids[0]
                    
                stock_move_ids_ok.append(stock_move_id)
                    
                product_id = self.pool.get("stock.move").browse(cr, uid, stock_move_id, context=context).product_id.id
                partial_data.update({'move'+unicode(stock_move_id):{'prodlot_id': False, 'product_id': product_id, 'product_uom': 1, 'product_qty': float(line['quantity'])}})
        
        delivered_pack_id = self.pool.get("stock.picking").do_partial(cr, uid, [delivery_order.id], partial_data, context)

        #Create Invoice based on delivery
        if delivered_pack_id.has_key(delivery_order.id) and delivered_pack_id[delivery_order.id]['delivered_picking']:
            if self.pool.get('stock.picking').browse(cr,uid, delivered_pack_id[delivery_order.id]['delivered_picking'],context=context).invoice_state=='2binvoiced':
                #Avoid adding delivery charges line
                self.pool.get('stock.picking').write(cr,uid,delivered_pack_id[delivery_order.id]['delivered_picking'],{'carrier_id':False},context)
                context['active_ids'] = [delivered_pack_id[delivery_order.id]['delivered_picking']]
                context['active_id'] = delivered_pack_id[delivery_order.id]['delivered_picking']
                wizard = {'journal_id':2}
                wizard_id = self.pool.get("stock.invoice.onshipping").create(cr, uid, wizard, context=context)
                res = self.pool.get("stock.invoice.onshipping").create_invoice(cr, uid, [wizard_id], context=context) 
        '''    
    @api.one
    def _process_dispatch_notification(self,document):
        if not document:
            return False
        
        origin = ''
        
        try:
            
            if not self._check_parties_delivery(document.element.header.dispatch_notification_info.parties.parties):
                self.error_message+=_('Delivery Address is not supplied in Landefeld dispatch notification')
                self.error_message+='/n'
                self.state = 'error'
                return True
            
            if not document.element.item_list.items:
                self.error_message+=_('No items in Landefeld dispatch notification')
                self.error_message+='/n'
                self.state = 'error'
                return True
            
            if self.get_control_type(document.element.header.control_info) == self.TYPE_OPENTRANS and not document.element.item_list:
                self.error_message+=_('No Order ID in Landefeld dispatch notification for OPENTRANS purchase order')
                self.state = 'error'
                return True
            
            purchase = self._search_order_ids_byref(document.element.item_list.items[0].item_udx.supplier_order_id,None)
            
            order_id = document.element.item_list.items[0].order_reference.order_id
            
            supplier_order_id = document.element.item_list.items[0].item_udx.supplier_order_id
            
            if not purchase:
                self.error_message+=_('No purchase order')
                self.error_message+='/n'
                self.state = 'error'
                return True
            
            if len(purchase) > 1:
                self.error_message+=_('Several purchases found with landefeld ref : %s') % unicode(supplier_order_id)
                self.error_message+='/n'
                self.state = 'error'
                return True
            
            origin += ' ' + purchase.name + ' '
            
            sale_orders = purchase.sale_ids
            
            
            if self.get_control_type(document.element.header.control_info) == self.TYPE_SHOP:
                internet_sale = self.env['sale.order'].search([('landefeld_ref','=',supplier_order_id)])
                if not internet_sale:
                    raise Exception("Sale order not found")
                if internet_sale[0] != sale_orders[0]:
                    purchase_sale = sale_orders[0]
                    raise Exception("Sale found by purchase and internet sale not match (%s / %s)"%(internet_sale.name,purchase_sale.name))
            
            #check if it's internet sale
            internet_sale = False
            automatic_sale = False
            delivery_order = None
            
            if sale_orders:
                sale = sale_orders[0]
                
                internet_sale = sale.landefeld_internet_sale
                automatic_sale = sale.landefeld_automatic_sale
                if automatic_sale or internet_sale:
                    origin += sale.name+' '
            
                if sale.landefeld_internet_sale and not purchase.landefeld_internet_purchase:
                    raise Exception("Internet sale and not internet purchase")
                if sale.landefeld_automatic_sale and not purchase.landefeld_automatic_purchase:
                    raise Exception("Automatic sale and not automatic purchase")
                if purchase.landefeld_internet_purchase and not sale.landefeld_internet_sale:
                    raise Exception("Internet purchase and not internet sale") 
                if purchase.landefeld_automatic_purchase and not sale.landefeld_automatic_sale:
                    raise Exception("Automatic purchase and not automatic sale")
                
                
            #generate in-invoice in case of internet or automatique sale
            if internet_sale or automatic_sale:
                purchase_invoice_id = purchase.action_invoice_create()
                purchase_invoice = self.env['account.invoice'].browse(purchase_invoice_id)
                purchase_invoice.invoice_line.write({'account_id':sale.section_id.purchase_account_id.id})
                
                
            if internet_sale or automatic_sale:
                if internet_sale:
                    self.edi_processor.edi_log('info','\n Internet sale : try to process delivery order')
                else:
                    self.edi_processor.edi_log('info','\n Automatic sale : try to process delivery order')
                    
                out_pickings = sale.picking_ids.filtered(lambda r:r.state not in ['done','cancel'] and r.picking_type_id.code == 'outgoing' or (r.picking_type_code =='incoming' and (r.location_dest_id.usage =='customer' and r.location_id.usage =='supplier')))
                        
                    
                #special case : no delivery order not done found
                if not out_pickings:
                    pickings_error = sale.picking_ids.filtered(lambda r:r.state not in ['cancel'] and r.picking_type_id.code == 'internal')
                    
                    if pickings_error:
                        raise Exception("ERROR : Internal picking found on internet or automatic sale !")
                    
                    every_sale_pickings = sale.picking_ids.filtered(lambda r:r.picking_type_id.code == 'outgoing' or (r.picking_type_code =='incoming' and (r.location_dest_id.usage =='customer' and r.location_id.usage =='supplier')))
                    if not every_sale_pickings : 
                        raise Exception("ERROR : No delivery order found for "+sale.name+" !")
                    else:
                        #check if all products of OpenTrans are in delivery orders done
                        for item in document.element.item_list.items:
                            qty_found = 0
                            products = self.env['product.product'].findByCode(item.product_id.supplier_pid)
                            for move in every_sale_pickings.move_lines:
                                if move.product_id in products:
                                    qty_found = qty_found + move.product_qty
                                    
                                    
                else:
                    #check customer
                    if internet_sale:
                        delivery_party = self._get_party_delivery(document.element.header.dispatch_notification_info.parties.parties)
                        for move_line in out_pickings.move_lines:
                            if not move_line.partner_id.landefeld_ref or move_line.partner_id.landefeld_ref != delivery_party.party_id:
                                self.error_message+='Partners landefeld ref does not match landefeld ref in OpenTrans is : "'+str(delivery_party.party_id)+'" and landefeld ref in "'+move_line.picking_id.name+'" is "'+str(move_line.partner_id.landefeld_ref)+'"'
                                self.error_message+='/n'
                                self.state = 'error'
                                return
                    
                    #Make the link between picking and edi message
                    for out_picking in out_pickings:
                        self.edi_message.res_id = out_picking.id
                        self.edi_message.model_name='stock.picking'
                        
                    #force availability
                    out_pickings.force_assign()
                    
                    
                    self._do_delivery(document,out_pickings)
                    
            if self.state=='draft':
                self.state='ok'
                
                
                
                
            if purchase:
                    purchase.landefeld_dispatchnote_received=True
            
        
        except Exception as e:
            if e.message == 'source_type_error':
                status = 'imported'
                #log = log+'\n Error : Source type 0 or undefined'
            else:
                status = 'error'                
                #log = log+'\n Error : '+unicode(e)+'\n'+traceback.format_exc()                
        '''
        if warning_mail:
            if purchase.validator and purchase.validator.user_email:
                if 'OpenTrans' in type_str:
                    self.send_warning_email(cr, uid, [import_landefeld_id], purchase.validator.user_email, _("OpenTrans Landefeld : Warning when validate dispatch note for "+origin), warning_mail, notify_other=True, context=context)
            
        #update log for import_landefelds    
        if status == 'imported':
            log = unicode(log) + '\n' + 'End Import successful at ' + unicode(datetime.today().strftime("%Y-%m-%d %H:%M"))
        elif status == 'warning':
            log = unicode(log) + '\n' + 'End Import with warning at ' + unicode(datetime.today().strftime("%Y-%m-%d %H:%M"))
        else:
            self.send_error_email(cr, uid,[import_landefeld_id], 'cth@elneo.com,dro@elneo.com', 'Landefeld dispatchnote imports failed', 'Landefeld dispatchnote imports failed at '+ unicode(datetime.today().strftime("%Y-%m-%d %H:%M")), context)
            log = unicode(log) + '\n' + 'End Import with error at ' + unicode(datetime.today().strftime("%Y-%m-%d %H:%M"))
            
        '''
                
        return True
                
                
    '''            
                
                #do partial delivery
                
                                   
    '''                            
                                
                                
    '''        
        
        for xml in xmls:
            #check errors
  
            
            #validate internet or automatique sale delivery order
            if internet_sale or automatic_sale:
                if internet_sale:
                    log = log + '\n Internet sale : try to process delivery order'
                else:
                    log = log + '\n Automatic sale : try to process delivery order'
                    
                for picking in sale.picking_ids:
                    if picking.type == 'out' and picking.state != 'done' and picking.state != 'cancel':
                        delivery_order = picking
                    if picking.type == 'internal' and picking.state != 'cancel':
                        raise Exception("ERROR : Internal picking found on internet or automatic sale !")
                    
                #special case : no delivery order not done found
                if not delivery_order:
                    out_pickings = [picking for picking in sale.picking_ids if picking.type == 'out']
                    if not out_pickings : 
                        raise Exception("ERROR : No delivery order found for "+sale.name+" !")
                    else:
                        #check if all products of OpenTrans are in delivery orders done
                        for line in xml['lines']:
                            qty_found = 0
                            product_ids = self.pool.get("product.product").findByCode(cr, uid, line['product_supplier_code'], context)
                            for out_picking in out_pickings:
                                for move in out_picking.move_lines:
                                    if move.product_id.id in product_ids:
                                        qty_found = qty_found + move.product_qty
                            #if float(line['quantity']) > float(qty_found):
                                #raise Exception("ERROR : in existing done delivery orders, product "+line['product_supplier_code']+" is not found or with less quantity than specified in OpenTrans")
                else:
                    #check customer
                    if internet_sale:
                        if not delivery_order.address_id or delivery_order.address_id.landefeld_ref != xml['supplier_delivery']['landefeld_partner_id']:
                            status = 'error'
                            error = 'Partners landefeld ref does not match landefeld ref in OpenTrans is : "'+str(xml['supplier_delivery']['landefeld_partner_id'])+'" and landefeld ref in "'+delivery_order.name+'" is "'+str(delivery_order.address_id.landefeld_ref)+'"'
                            log = log + '\n '+error
                            raise Exception("Partners landefeld ref does not match")

                    #force availability
                    self.pool.get("stock.picking").force_assign(cr, uid, [picking.id]) 
                    
                    #do partial delivery
                    
                    partial_data = {
                        'delivery_date':xml['create_date'], 
                    }
                    
                    stock_move_ids_ok = []
                    for line in xml['lines']:
                        
                        if float(line['quantity']) > 0:
                            product_ids = self.pool.get("product.product").findByCode(cr, uid, line['product_supplier_code'], context)
                        
                            if not product_ids:
                                warning_message = _("Error when validating dispatch note from Landefeld : Product %s not found in database.")%(line['product_supplier_code'],)
                                warning_mail = warning_mail + warning_message + '\n'
                                raise Exception("Product "+line['product_supplier_code']+" not found in database")
                            
                            stock_move_ids = self.pool.get("stock.move").search(cr, uid, [('product_id','in',product_ids), ('picking_id','=',delivery_order.id)])
                            stock_move_ids = [m for m in stock_move_ids if (m not in stock_move_ids_ok)]
                        
                            if not stock_move_ids:
                                warning_mail = warning_mail + _("Error when validating dispatch note from Landefeld : Product %s not found in delivery picking %s.")%(line['product_supplier_code'],delivery_order.name)
                                warning_mail = warning_mail + '\n'
                                raise Exception("Product "+line['product_supplier_code']+" not found in "+delivery_order.name)
                            elif len(stock_move_ids) > 1:
                                stock_move_id = None
                                alternative_stock_move_id = None
                                for stock_move in self.pool.get("stock.move").browse(cr, uid, stock_move_ids, context):
                                    if float(line['quantity']) == stock_move.product_qty:
                                        stock_move_id = stock_move.id
                                    if float(line['quantity']) < stock_move.product_qty:
                                        alternative_stock_move_id = stock_move.id
                                if not stock_move_id:
                                    stock_move_id = alternative_stock_move_id
                                if not stock_move_id:                    
                                    warning_mail = warning_mail + _("Error when validating dispatch note from Landefeld : No product %s found in delivery picking %s for quantity %s.")%(line['product_supplier_code'],delivery_order.name, unicode(line['quantity']))
                                    warning_mail = warning_mail + '\n'
                                    raise Exception("Several products "+line['product_supplier_code']+" found in "+delivery_order.name)
                            else:
                                stock_move_id = stock_move_ids[0]
                                
                            stock_move_ids_ok.append(stock_move_id)
                                
                            product_id = self.pool.get("stock.move").browse(cr, uid, stock_move_id, context=context).product_id.id
                            partial_data.update({'move'+unicode(stock_move_id):{'prodlot_id': False, 'product_id': product_id, 'product_uom': 1, 'product_qty': float(line['quantity'])}})
                    
                    delivered_pack_id = self.pool.get("stock.picking").do_partial(cr, uid, [delivery_order.id], partial_data, context)

                    #Create Invoice based on delivery
                    if delivered_pack_id.has_key(delivery_order.id) and delivered_pack_id[delivery_order.id]['delivered_picking']:
                        if self.pool.get('stock.picking').browse(cr,uid, delivered_pack_id[delivery_order.id]['delivered_picking'],context=context).invoice_state=='2binvoiced':
                            #Avoid adding delivery charges line
                            self.pool.get('stock.picking').write(cr,uid,delivered_pack_id[delivery_order.id]['delivered_picking'],{'carrier_id':False},context)
                            context['active_ids'] = [delivered_pack_id[delivery_order.id]['delivered_picking']]
                            context['active_id'] = delivered_pack_id[delivery_order.id]['delivered_picking']
                            wizard = {'journal_id':2}
                            wizard_id = self.pool.get("stock.invoice.onshipping").create(cr, uid, wizard, context=context)
                            res = self.pool.get("stock.invoice.onshipping").create_invoice(cr, uid, [wizard_id], context=context)
            else:
                log = log + '\n Classic purchase'
                
            if purchase:
                self.pool.get("purchase.order").write(cr, uid, purchase.id, {'landefeld_dispatchnote_received':True}, context=context)
                
            
        if status == 'draft': 
            status = 'imported'
        
    except Exception as e:
        if e.message == 'source_type_error':
            status = 'imported'
            log = log+'\n Error : Source type 0 or undefined'
        else:
            status = 'error'                
            log = log+'\n Error : '+unicode(e)+'\n'+traceback.format_exc()                

    if warning_mail:
        if purchase.validator and purchase.validator.user_email:
            if 'OpenTrans' in type_str:
                self.send_warning_email(cr, uid, [import_landefeld_id], purchase.validator.user_email, _("OpenTrans Landefeld : Warning when validate dispatch note for "+origin), warning_mail, notify_other=True, context=context)
        
    #update log for import_landefelds    
    if status == 'imported':
        log = unicode(log) + '\n' + 'End Import successful at ' + unicode(datetime.today().strftime("%Y-%m-%d %H:%M"))
    elif status == 'warning':
        log = unicode(log) + '\n' + 'End Import with warning at ' + unicode(datetime.today().strftime("%Y-%m-%d %H:%M"))
    else:
        self.send_error_email(cr, uid,[import_landefeld_id], 'cth@elneo.com,dro@elneo.com', 'Landefeld dispatchnote imports failed', 'Landefeld dispatchnote imports failed at '+ unicode(datetime.today().strftime("%Y-%m-%d %H:%M")), context)
        log = unicode(log) + '\n' + 'End Import with error at ' + unicode(datetime.today().strftime("%Y-%m-%d %H:%M"))
    
    self.write(cr, uid,dispatchnote.id, 
                                   {'log' :log,
                                    'status':status, 
                                    'end_date':datetime.today(),
                                    'origin':origin
                                             }, context)
    
    '''
    
    @api.one
    def _process_landefeld_document(self,document):
        
        if self.edi_message.type.usage =='outgoing':
            wizard = self.env['landefeld.edi.export'].create({'message_id':self.edi_message.id})
            wizard._transmit()
            self.state = wizard.state
        elif self.edi_message.type.usage =='incoming':
            if document.element.__class__.__name__=='OpenTransOrderResponse':
                self._process_order_response(document)
            elif document.element.__class__.__name__ == 'OpenTransDispatchNotification':
                self._process_dispatch_notification(document)
        else:
            return
