from openerp import models, fields, api, _
from openerp.exceptions import Warning
from openerp.addons.edi_opentrans.edi_opentrans import OpenTransOrder,OpenTransOrderItemList, OpenTransOrderItem, OpenTransParty,OpenTransAddress, OpenTransOrderPartiesReference
from datetime import datetime

from xml.dom import minidom
from StringIO import *
import base64
from xml.etree.ElementTree import ElementTree,Element, SubElement, tostring, fromstring
import traceback
from ftplib import FTP

class LandefeldEdiExport(models.TransientModel):
    _name='landefeld.edi.export'
    
    purchase_id = fields.Many2one('purchase.order',string='Purchase Order',help='Purchase Order that launch the export')
    
    message_id = fields.Many2one('edi.message',string='EDI Message')
    
    warning_message = fields.Text('Warning Message',default='')
    error_message = fields.Text('Error Message',default='')
    
    state = fields.Selection([('draft','Draft'),('ok','OK'),('warning','Warning'),('error','Error')],default='draft')
    
    
    @api.multi
    def write(self,vals):
        if vals.has_key('warning_message') and vals['warning_message']:
            vals.update({'state':'warning'})
            
        if vals.has_key('error_message') and vals['error_message']:
            vals.update({'state':'error'})
    
        super(LandefeldEdiExport,self).write(vals)

    def _export(self):
        
        for order in self.purchase_id:
            res = self._create_trans_document()
            
            #write xml-file 
            filename = '%s-%s-%s.xml' % (
                    order.name, 
                    datetime.today().strftime("%Y%m%d"),
                    str(self.id).zfill(7)[-7:],
                )
            
            file_buffer =  StringIO()
            ElementTree(res).write(file_buffer, xml_declaration=True,  encoding="utf-8")
            
            file_buffer = tostring(res,encoding="utf-8",method='xml')
            file_buffer = minidom.parseString(file_buffer)
            file_buffer= file_buffer.toprettyxml(indent="  ", newl="\r\n", encoding="UTF-8")
            
            
            m_type = self.env['edi.message.type'].search([('usage','=','outgoing'),('processor.processor_type','=','landefeld')])
            
            if not m_type:
                raise Warning(_("Configuration Error.\n\nYou don't have an EDI Message Type configured for Landefeld exports. Please contact your administrator"))
            
            message = self.env['edi.message'].create({'type':m_type.id,'origin':order.name,'model':'purchase.order','res_id':self.purchase_id.id})
            
            att_id = self.env['ir.attachment'].create({
                            'res_id': message.id,
                            'res_model': 'edi.message',
                            'name': filename,
                            'datas_fname':filename, 
                            'datas': base64.encodestring(file_buffer),
                        })
            
            message.state = 'confirmed'
            
        return True
        
    def _transmit(self):
        
        if not self.env['production.server'].is_production_server():
            return True
        
        
        '''    
        if not '10.0.0.117' in os.popen("cat /etc/network/interfaces | grep address","r").read()[8:]:
            return True
        '''
        
        if self.message_id and self.message_id.type.usage =='outgoing':
            try:
                attachment = self.message_id.attachment_ids and self.message_id.attachment_ids[0]
                
                ftp_isPassive = self.env['ir.config_parameter'].get_param('elneo_landefeld.ftp_isPassive','False')
                if self.env['ir.config_parameter'].get_param('elneo_landefeld.ftp_isPassive','False') == 'True':
                    ftp_isPassive=True
                else:
                    ftp_isPassive=False
                ftp_port = int(self.env['ir.config_parameter'].get_param('elneo_landefeld.ftp_port','False'))
                ftp_host = str(self.env['ir.config_parameter'].get_param('elneo_landefeld.ftp_host','False'))
                ftp_user = str(self.env['ir.config_parameter'].get_param('elneo_landefeld.ftp_user','False'))
                ftp_password = str(self.env['ir.config_parameter'].get_param('elneo_landefeld.ftp_password','False'))
                ftp_export_dir = self.env['ir.config_parameter'].get_param('elneo_landefeld.ftp_export_dir','False')
 
                connection=FTP()                    
                connection.set_pasv(ftp_isPassive)
                connection.connect(ftp_host,ftp_port,10)
                connection.login(ftp_user,ftp_password)
                
                connection.cwd(ftp_export_dir)    
                
                
                connection.storlines("STOR " + attachment.datas_fname, StringIO(base64.decodestring(attachment.datas)))
                
                
                connection.quit()
                
                self.state='ok'
                
                self.message_id.message_post(body='File sent at ' + datetime.today().strftime("%Y-%m-%d %H:%M"))
                
            except Exception, e:
                #update log for import_landefelds
                log = '\n Error when sending OpenTrans file to FTP : '
                if str(e):
                    log = log + str(e)
                if traceback.format_exc():
                    log = log + '\n'+traceback.format_exc()    
                self.error_message += log
                

        
    @api.model
    def _create_trans_document(self):

        open_order = None
        open_order = OpenTransOrder()
        
        # ORDER REFERENCE
        if (self.purchase_id.sale_ids and self.purchase_id.sale_ids[0].client_order_ref):
            open_order.order_header.order_info.order_id = self.purchase_id.name+'//'+self.purchase_id.sale_ids[0].client_order_ref
        else:
            open_order.order_header.order_info.order_id = self.purchase_id.name
        
        # ORDER DATE
        open_order.order_header.order_info.order_date = datetime.strptime(self.purchase_id.date_order, '%Y-%m-%d %H:%M:%S').strftime("%Y-%m-%dT%H:%M:%S+01:00")
        
        
        # SUPPLIER
        supplier = self._get_supplier_trans()
        open_order.order_header.order_info.parties.parties.append(supplier)
            
        # BUYER
        buyer = self._get_buyer_trans()
        open_order.order_header.order_info.parties.parties.append(buyer)
        
        # ORDER PARTIES REFERENCE
        open_order.order_header.order_info.parties_reference = OpenTransOrderPartiesReference()
        open_order.order_header.order_info.parties_reference.buyer_idref = buyer.party_id
        
        
        # DELIVERY
        delivery = self._get_delivery_trans()
        open_order.order_header.order_info.parties.parties.append(delivery)
        
        #HEADER_UDX
        #set neutral if direct delivery to Customer
        if self.purchase_id.dest_address_id:
            open_order.order_header.order_info.header_udx.neutral = "Standard"
        
        # ITEMS
        open_order.item_list, total_items,total_value = self._get_items_trans()
        
        #SUMMARY
        open_order.summary.total_amount = total_value
        open_order.summary.total_item_num = total_items

            
        return open_order.getOpenTrans()
    
    def _get_items_trans(self):
        order_item_list = OpenTransOrderItemList()
        
        total_item_number_value = 0
        total_amount_value = 0
        for purchase_order_line in self.purchase_id.order_line:
            total_item_number_value = total_item_number_value+ purchase_order_line.product_qty
            total_amount_value = total_amount_value+(purchase_order_line.price_unit * purchase_order_line.product_qty)
            
            order_item = OpenTransOrderItem()
            order_item.line_item_id = str(purchase_order_line.id)
            
       
            for supplier in purchase_order_line.product_id.seller_ids.filtered(lambda r:r.name.id==self.purchase_id.partner_id.id):
                order_item.product_id.supplier_pid = supplier.product_code
                
            order_item.product_id.description_short = purchase_order_line.name
            
            order_item.quantity = str(purchase_order_line.product_qty)
            order_item.order_unit = purchase_order_line.product_uom.name == 'PCE' and 'pc.' or purchase_order_line.product_uom.name
            
            order_item.price_line_amount = str(purchase_order_line.price_unit * purchase_order_line.product_qty)
            
            order_item_list.order_items.append(order_item)
            
        return order_item_list, total_item_number_value,total_amount_value
    
    
            
            
    def _get_supplier_trans(self):
        
        party_supplier = None
        if (self.purchase_id.partner_id):

            party_supplier = OpenTransParty(role="supplier",type="buyer_specific")
            party_address = OpenTransAddress()
            
            party_address.name = self.purchase_id.partner_id.name
            if (self.purchase_id.partner_id.street2):
                party_address.name2 = self.purchase_id.partner_id.street
                party_address.street = self.purchase_id.partner_id.street2
            else:
                party_address.street = self.purchase_id.partner_id.street
            
            party_address.zip = self.purchase_id.partner_id.zip
            party_address.city = self.purchase_id.partner_id.city
            party_address.country = self.purchase_id.partner_id.country_id.name
            party_address.country_coded = self.purchase_id.partner_id.country_id.code
            
            
            party_supplier.address = party_address
            
        return party_supplier
        
    
    def _get_buyer_trans(self):
        
        address_invoice = self.purchase_id.company_id.partner_id.child_ids.filtered(lambda r:r.type == 'invoice')
            
        address_default = self.purchase_id.company_id.partner_id
        if address_default:
            buyer_ref = address_default.landefeld_ref
            
        if not address_invoice:
            address = address_default
        else:
            address = address_invoice
            
        party_buyer=OpenTransParty(role="buyer")
        
        party_buyer.party_id = buyer_ref
        party_buyer.address = OpenTransAddress()
        party_buyer.address.name = address.name
        party_buyer.address.street = address.street
        if address.street2:
            party_buyer.address.street += address.street2
            
        party_buyer.address.zip = address.zip
        party_buyer.address.city = address.city
        party_buyer.address.country = address.country_id.name
        party_buyer.address.country_coded = address.country_id.code
       
        
        
        return party_buyer
        
        
    def _get_delivery_trans(self):
        
        party_delivery = OpenTransParty(role="delivery")
        
        
        # DIRECT DELIVERY
        if self.purchase_id.picking_type_id and self.purchase_id.picking_type_id.default_location_src_id.usage == 'supplier' and self.purchase_id.picking_type_id.default_location_dest_id.usage == 'customer' and self.purchase_id.dest_address_id:
            delivery_address = self.purchase_id.dest_address_id
        elif self.purchase_id.picking_type_id and self.purchase_id.picking_type_id.code == 'incoming':
            warehouse = self.purchase_id.picking_type_id.warehouse_id
            delivery_address = warehouse.partner_id
            
        if not delivery_address:
            raise Warning(_('OPENTRANS ERROR'),_('Can\'t find delivery address for purchase. Maybe the address is not defined on the partner '))
        
        
        if delivery_address.name and delivery_address.parent_id and delivery_address.parent_id.name:
            party_delivery.address.name = delivery_address.parent_id.name + ' - ' + delivery_address.name
        elif delivery_address.parent_id and delivery_address.parent_id.name:
            party_delivery.address.name = delivery_address.parent_id.name
        elif delivery_address.name :
            # Delivery address == company
            party_delivery.address.name = delivery_address.name
        else:
            raise Warning(_('The name of the delivery address is not defined!'))
        
        party_delivery.party_id = delivery_address.landefeld_ref
        
        if delivery_address.street2:
            party_delivery.address.name2 = delivery_address.street
            party_delivery.address.street = delivery_address.street2
        else:
            party_delivery.address.street=delivery_address.street
            
        party_delivery.address.city = delivery_address.city
        party_delivery.address.zip = delivery_address.zip
        party_delivery.address.country = delivery_address.country_id.name
        party_delivery.address.country_coded = delivery_address.country_id.code
            
        
        return party_delivery  