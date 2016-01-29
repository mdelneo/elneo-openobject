from openerp import models, api, _
from openerp.exceptions import Warning

from edi_opentrans import *
from datetime import datetime
from xml.dom import minidom
from StringIO import *
import base64


'''
class PurchaseOrder(models.Model):
    
    _inherit = 'purchase.order'
 
    @api.model
    def edi_export(self, records, edi_struct=None):
        res = super(PurchaseOrder,self).edi_export(records, edi_struct=None)
        
        if self.env.context.get('edi_opentrans',False):
            for record in records:
                record._edi_opentrans_export()
        
        return res
    
    @api.multi
    def button_edi_export(self):
        for order in self:
            self.env['purchase.order'].with_context(edi_opentrans=True).edi_export([order])
        
        return True
        
        
    
    def _edi_opentrans_export(self):
        
        for order in self:
            res = order._create_trans_document()
            
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
            
            att_id = self.env['ir.attachment'].create({
                            'res_id': order.id,
                            'res_model': order._name,
                            'name': filename,
                            'datas_fname':filename, 
                            'datas': base64.encodestring(file_buffer),
                        })
        return True
        
    @api.model
    def _create_trans_document(self):

        open_order = None
        open_order = OpenTransOrder()
        
        # ORDER REFERENCE
        if (self.sale_ids and self.sale_ids[0].client_order_ref):
            open_order.order_header.order_info.order_id = self.name+'//'+self.sale_ids[0].client_order_ref
        else:
            open_order.order_header.order_info.order_id = self.name
        
        # ORDER DATE
        open_order.order_header.order_info.order_date = datetime.strptime(self.date_order, '%Y-%m-%d %H:%M:%S').strftime("%Y-%m-%dT%H:%M:%S+01:00")
        
        
        # SUPPLIER
        supplier = self._get_supplier_trans()
        open_order.order_header.order_info.parties.parties.append(supplier)
            
        # BUYER
        buyer = self._get_buyer_trans()
        open_order.order_header.order_info.parties.parties.append(buyer)
        
        # DELIVERY
        delivery = self._get_delivery_trans()
        open_order.order_header.order_info.parties.parties.append(delivery)
        
        #HEADER_UDX
        #set neutral if direct delivery to Customer
        if self.dest_address_id:
            open_order.order_header.order_info.header_udx.neutral = "Standard"
        
        # ITEMS
        open_order.item_list = self._get_items_trans()

            
        return open_order.getOpenTrans()
    
    def _get_items_trans(self):
        order_item_list = OpenTransOrderItemList()
        
        total_item_number_value = 0
        total_amount_value = 0
        for purchase_order_line in self.order_line:
            total_item_number_value = total_item_number_value+ purchase_order_line.product_qty
            total_amount_value = total_amount_value+(purchase_order_line.price_unit * purchase_order_line.product_qty)
            
            order_item = OpenTransOrderItem()
            order_item.line_item_id = str(purchase_order_line.id)
            
       
            for supplier in purchase_order_line.product_id.seller_ids.filtered(lambda r:r.name.id==self.partner_id.id):
                order_item.product_id.supplier_pid = supplier.product_code
                
            order_item.product_id.description_short = purchase_order_line.name
            
            order_item.quantity = str(purchase_order_line.product_qty)
            order_item.order_unit = purchase_order_line.product_uom.name
            
            order_item.price_line_amount = str(purchase_order_line.price_unit * purchase_order_line.product_qty)
            
            order_item_list.order_items.append(order_item)
            
        return order_item_list
            
            
    def _get_supplier_trans(self):
        
        party_supplier = None
        if (self.partner_id):

            party_supplier = OpenTransParty(role="supplier",type="buyer_specific")
            party_address = OpenTransAddress()
            
            party_address.name = self.partner_id.name
            if (self.partner_id.street2):
                party_address.name2 = self.partner_id.street
                party_address.street = self.partner_id.street2
            else:
                party_address.street = self.partner_id.street
            
            party_address.zip = self.partner_id.zip
            party_address.city = self.partner_id.city
            party_address.country = self.partner_id.country_id.name
            party_address.country_coded = self.partner_id.country_id.code
            
            
            party_supplier.address = party_address
            
        return party_supplier
        
    
    def _get_buyer_trans(self):
        
        address_invoice = self.company_id.partner_id.child_ids.filtered(lambda r:r.type == 'invoice')
            
        address_default = self.company_id.partner_id
        #if address_default:
            #buyer_ref = address_default.landefeld_ref
            
        if not address_invoice:
            address = address_default
        else:
            address = address_invoice
            
        party_buyer=OpenTransParty(role="buyer")
        
        party_buyer.party_id = address.id
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
        if self.dest_address_id:
            delivery_address = self.dest_address_id
        else:
            warehouse_id = self.env['stock.location'].get_warehouse(self.location_id)
            warehouse = self.env['stock.warehouse'].browse(warehouse_id)
            delivery_address = warehouse.partner_id
            
        if not delivery_address:
            raise Warning(_('OPENTRANS ERROR'),_('Can\'t find delivery address.'))
        
        party_delivery.address.name = delivery_address.name
        
        party_delivery.party_id = delivery_address.id
        
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
'''