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
from xml.etree.ElementTree import ElementTree,Element, SubElement, tostring, fromstring
from xml.dom import minidom
from datetime import datetime

from openerp import models, fields, api

class OpenTransElement(object):
    
    def createFromNode(self,node):
        return True
    
    def createFromXML(self,xml):
        return Element(xml)
   
    def getOpenTrans(self,tag=None):
        return Element(tag)
        

class OpenTransOrderControlInfo(OpenTransElement):
    
    def __init__(self):
        super(OpenTransOrderControlInfo,self).__init__()
        self.generation_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+01:00")
    
    generation_date = ""
    generator_info = ""
    
    def createFromNode(self, node):
        info = node.find("GENERATOR_INFO")
        date = node.find("GENERATION_DATE")
        if info is not None:
            self.generator_info = info.text
        if date is not None:
            self.generation_date = date.text
        
            return self
                        
        return OpenTransElement.createFromNode(self, node)

    def getOpenTrans(self,tag=None):
        res=super(OpenTransOrderControlInfo,self).getOpenTrans('CONTROL_INFO')
        
        date = SubElement(res, 'GENERATION_DATE')
        date.text = self.generation_date
        
        if self.generator_info:
            gen = SubElement(res, 'GENERATOR_INFO')
            gen.text = self.generation_date
        
        return res
    

class OpenTransAddress(OpenTransElement):
    
    name = ""
    name2 = ""
    street = ""
    zip=""
    city=""
    country=""
    country_coded=""
    
    def __init__(self):
        super(OpenTransAddress,self).__init__()
        self.name = ""
        
    def createFromNode(self, node):
        name = node.find('NAME')
        name2 = node.find('NAME2')
        street = node.find('STREET')
        zip = node.find('ZIP')
        city = node.find('CITY')
        country = node.find('COUNTRY')
        country_coded = node.find('COUNTRY_CODED')
        
        if name is not None:
            self.name = name.text
        if name2 is not None:
            self.name2 = name2.text
        if street is not None:
            self.street = street.text
        if zip is not None:
            self.zip = zip.text
        if city is not None:
            self.city = city.text
        if country is not None:
            self.country = country.text
        if country_coded is not None:
            self.country_coded = country_coded.text
        
        
        return OpenTransElement.createFromNode(self, node)
    
    def getOpenTrans(self):
        res = super(OpenTransAddress,self).getOpenTrans('ADDRESS')

        name = SubElement(res,'bmecat:NAME')
        name.text = self.name
        if self.name2 != "":
            name2 = SubElement(res,'bmecat:NAME2')
            name2.text = self.name2
        street = SubElement(res, 'bmecat:STREET')
        street.text = self.street
        zip = SubElement(res, 'bmecat:ZIP')
        zip.text=self.zip
        city=SubElement(res, 'bmecat:CITY')
        city.text=self.city
        country = SubElement(res,'bmecat:COUNTRY')
        country.text=self.country
        country_coded = SubElement(res,'bmecat:COUNTRY_CODED')
        country_coded.text = self.country_coded
        
        return res
    
class OpenTransAccount(OpenTransElement):
    
    holder = ""
    bank_account = ""
    bank_account_type=""
    bank_code=""
    bank_code_type=""
    
    def __init__(self):
        super(OpenTransAccount,self).__init__()
        self.holder = ""
        self.bank_account = ""
        self.bank_account_type=""
        self.bank_code = ""
        self.bank_code_type = ""
        
    def createFromNode(self, node):
        holder = node.find('HOLDER')
        bank_account = node.find('BANK_ACCOUNT')
        bank_code = node.find('BANK_CODE')
        
        if holder is not None:
            self.holder = holder.text
        if bank_account is not None:
            self.bank_account = bank_account.text
            if bank_account.attrib.has_key('type'):
                self.bank_account_type=bank_account.attrib['type']
                
        if bank_code is not None:
            self.bank_code = bank_code.text
            if bank_code.attrib.has_key('type'):
                self.bank_code_type=bank_code.attrib['type']

        return OpenTransElement.createFromNode(self, node)
    
    def getOpenTrans(self):
        res = super(OpenTransAccount,self).getOpenTrans('ACCOUNT')
        
        if (self.holder == "" and self.bank_account == "" and self.bank_account_type=="" and self.bank_code=="" and self.bank_code_type==""):
            return None

        holder = SubElement(res,'HOLDER')
        holder.text = self.holder
        
        
        bank_account = SubElement(res,'BANK_ACCOUNT')
        bank_account.text = self.bank_account
        if self.bank_account_type and self.bank_account_type!= "":
            bank_account.attrib['type']=self.bank_account_type
            
        bank_code = SubElement(res,'BANK_CODE')
        bank_code.text = self.bank_code
        if self.bank_code_type and self.bank_code_type!= "":
            bank_code.attrib['type']=self.bank_code_type
        
        return res

class OpenTransParty(OpenTransElement):
    
    party_id = ""
    party_role = ""
    type=""
    address = OpenTransAddress
    account = OpenTransAccount
    
    def __init__(self,id="",role="",type="supplier_specific"):
        super(OpenTransParty,self).__init__()
        self.party_id = id
        self.party_role=role
        self.type=type
        self.address = OpenTransAddress()
        self.account = OpenTransAccount()
        
    def createFromNode(self, node):
        party_id = node.find('PARTY_ID')
        party_role = node.find('PARTY_ROLE')
        party_address = node.find('ADDRESS')
        account=node.find('ACCOUNT')
        if party_id is not None:
            self.party_id = party_id.text
            if party_id.attrib.has_key('type'):
                self.type = party_id.attrib['type']
        if party_role is not None:
            self.party_role = party_role.text
        if party_address is not None:
            self.address.createFromNode(party_address)
        
        if account is not None:
            self.account.createFromNode(account)
        else:
            self.account = None
        
        return OpenTransElement.createFromNode(self, node)
    
    def getOpenTrans(self):
        
        res= super(OpenTransParty,self).getOpenTrans('PARTY')
        
        
        party_id = SubElement(res, 'bmecat:PARTY_ID')
        party_id.attrib['type']=self.type
        
        if self.party_id:
            party_id.text = str(self.party_id)
        
        party_role = SubElement(res, 'PARTY_ROLE')
        party_role.text = self.party_role
        
        if self.address:
            address = self.address.getOpenTrans()
            res.append(address)
        
            account = self.account.getOpenTrans()
            if account:
                res.append(account)
        
        
        return res
    
class OpenTransParties(OpenTransElement):
    parties = []
    
    def __init__(self):
        super(OpenTransParties,self).__init__()
        self.parties = []
        
    def createFromNode(self, node):
                
        for party in node:
            the_party = OpenTransParty()
            the_party.createFromNode(party)
            self.parties.append(the_party)
        return OpenTransElement.createFromNode(self, node)
    
    def getOpenTrans(self):
        parties = super(OpenTransParties,self).getOpenTrans('PARTIES')
        for party in self.parties:
            parties.append(party.getOpenTrans())
        return parties
    
class OpenTransOrderPartiesReference(OpenTransElement):
    buyer_idref = ""
    supplier_idref = ""
    
    def __init__(self):
        super(OpenTransOrderPartiesReference,self).__init__()
        self.buyer_idref=""
        self.supplier_idref=""
        
    def createFromNode(self, node):
        
        return OpenTransElement.createFromNode(self, node)
    
    def getOpenTrans(self):
        res = super(OpenTransOrderPartiesReference,self).getOpenTrans('ORDER_PARTIES_REFERENCE')
        buyer = SubElement(res,'bmecat:BUYER_IDREF')
        buyer.text = self.buyer_idref
        supplier = SubElement(res, 'bmecat:SUPPLIER_IDREF')
        supplier.text = self.supplier_idref
        return res
    
class OpenTransHeaderUDX(OpenTransElement):
    neutral = ""
    shipment_method=""
    customer_no=""
    payment_term=""
    
    def __init__(self):
        super(OpenTransHeaderUDX,self).__init__()
        self.neutral=""
        
    def createFromNode(self, node):
        
        shipment_method = node.find('UDX_SHIPMENT_METHOD')
        if shipment_method is not None:
            self.shipment_method = shipment_method.text
        
        customer_no = node.find('UDX_CUSTOMER_NO')
        if customer_no is not None :
            self.customer_no = customer_no.text
            
        payment_term = node.find('UDX_PAYMENT_TERM')
        if payment_term is not None:
            self.payment_term = payment_term.text
            
        neutral = node.find('UDX_SHIPMENT_NEUTRAL')
        if neutral is not None:
            self.neutral = neutral.text  
        
        return OpenTransElement.createFromNode(self, node)
        
    def getOpenTrans(self, tag=None):
        res = super(OpenTransHeaderUDX,self).getOpenTrans('HEADER_UDX')
        
        if self.neutral != "":
            neutral = SubElement(res, 'UDX_SHIPMENT_NEUTRAL')
            neutral.text = self.neutral
            
        if self.shipment_method != "":
            shipment_method = SubElement(res,'UDX_SHIPMENT_METHOD')
            shipment_method.text = self.shipment_method
            
        if self.customer_no != "":
            customer_no = SubElement(res,'UDX_CUSTOMER_NO')
            customer_no.text = self.customer_no
            
        if self.payment_term != "":
            payment_term = SubElement(res,'UDX_PAYMENT_TERM')
            payment_term.text = self.payment_term
    
        return res
    
class OpenTransOrderInfo(OpenTransElement):
    
    order_id = ""
    order_date = ""
    parties = OpenTransParties()
    parties_reference = None
    header_udx = None
    
    def __init__(self):
        super(OpenTransOrderInfo,self).__init__()
        self.parties = OpenTransParties()
        self.parties_reference = OpenTransOrderPartiesReference()
        self.header_udx = OpenTransHeaderUDX()
        self.order_date=""
        self.order_id=""
        
    def getOpenTrans(self, tag=None):
        res = super(OpenTransOrderInfo,self).getOpenTrans('ORDER_INFO')
        
        order_id = SubElement(res,'ORDER_ID')
        order_id.text = self.order_id
        
        order_date = SubElement(res, 'ORDER_DATE')
        order_date.text = self.order_date
        
        res.append(self.parties.getOpenTrans())
        
        res.append(self.parties_reference.getOpenTrans())
        
        res.append(self.header_udx.getOpenTrans())
        
        
        return res

class OpenTransDeliveryDate(OpenTransElement):
    
    delivery_start_date = ""
    delivery_end_date = ""
    type = ""
    
    def __init__(self):
        super(OpenTransDeliveryDate,self).__init__()
        self.type = ""
        
    def createFromNode(self, node):
        if node.tag =='DELIVERY_DATE' and node.attrib.has_key('type'):
            self.type = node.attrib['type']
            
        s_date = node.find('DELIVERY_START_DATE')
        e_date = node.find('DELIVERY_END_DATE')
        if s_date is not None:
            self.delivery_start_date = s_date.text
        if e_date is not None:
            self.delivery_end_date = e_date.text
        
        return OpenTransElement.createFromNode(self, node)
        
    def getOpenTrans(self, tag=None):
        res = super(OpenTransDeliveryDate,self).getOpenTrans('DELIVERY_DATE')
        
        delivery_start_date = SubElement(res,'DELIVERY_START_DATE')
        delivery_start_date.text = self.delivery_start_date
        
        delivery_end_date = SubElement(res,'DELIVERY_END_DATE')
        delivery_end_date.text = self.delivery_end_date
        
        return res
    
class OpenTransMeansOfTransport(OpenTransElement):
    
    transport_id = ""
    transport_name = ""
    transport_type=""
    
    def __init__(self):
        super(OpenTransDeliveryDate,self).__init__()
        self.transport_id = ""
        self.transport_name = ""
        
    def createFromNode(self, node):
        
        t_id = node.find('MEANS_OF_TRANSPORT_ID')
        name = node.find('MEANS_OF_TRANSPORT_NAME')
        
        if node.attrib.has_key('type'):
            self.transport_type = node.attrib('type')
        
        if t_id is not None:
            self.transport_id = t_id.text
        if name is not None:
            self.transport_name = name.text
        
        return OpenTransElement.createFromNode(self, node)
        
    def getOpenTrans(self, tag=None):
        res = super(OpenTransMeansOfTransport,self).getOpenTrans('MEANS_OF_TRANSPORT')
        
        t_id = SubElement(res,'MEANS_OF_TRANSPORT_ID')
        t_id.text = self.transport_id
        
        transport_name = SubElement(res,'MEANS_OF_TRANSPORT_NAME')
        transport_name.text = self.transport_name
        
        if self.transport_type:
            res.attrib['type'] = self.transport_type
        
        return res
    
class OpenTransLogisticDetailsInfo(OpenTransElement):
    means_of_transport = OpenTransMeansOfTransport
    
    def __init__(self):
        super(OpenTransLogisticDetailsInfo,self).__init__()
        self.means_of_transport = OpenTransMeansOfTransport()
        
    def createFromNode(self, node):
        
        transport = node.find('MEANS_OF_TRANSPORT')
        self.means_of_transport.createFromNode(transport)
        
        return OpenTransElement.createFromNode(self, node)
        
    def getOpenTrans(self, tag=None):
        res = super(OpenTransLogisticDetailsInfo,self).getOpenTrans('LOGISTIC_DETAILS_INFO')
        
        res.append(self.means_of_transport.getOpenTrans())
        
        return res
    
class OpenTransDispatchNotificationInfo(OpenTransElement):
    
    notification_id = ""
    notification_date = ""
    parties = OpenTransParties
    delivery_date=OpenTransDeliveryDate
    supplier_idref = ""
    buyer_idref=''
    parties_reference = None
    header_udx = None
    customer_no = ""
    logistic_details_info = OpenTransLogisticDetailsInfo
    remarks=[]
    
    def __init__(self):
        super(OpenTransDispatchNotificationInfo,self).__init__()
        self.parties = OpenTransParties()
        self.parties_reference = OpenTransOrderPartiesReference()
        self.header_udx = OpenTransHeaderUDX()
        self.delivery_date=OpenTransDeliveryDate()
        self.order_id=""
        
    def createFromNode(self, node):
        
        order_id = node.find('ORDER_ID')
        date = node.find('ORDERRESPONSE_DATE')
        supplier_order_id = node.find('SUPPLIER_ORDER_ID')
        delivery_date = node.find('DELIVERY_DATE')
        if order_id is not None:
            self.order_id = order_id.text
        if date is not None:
            self.order_response_date = date.text
        if supplier_order_id is not None:
            self.supplier_order_id = supplier_order_id.text
            
        parties = node.find('PARTIES')
        if parties is not None :
            self.parties.createFromNode(parties)
        
        part_ref = node.find('ORDER_PARTIES_REFERENCE')
        if part_ref is not None:
            self.parties_reference.createFromNode(part_ref)
            
        customer_no = node.find('CUSTOMER_NO')
        if customer_no is not None:
            self.customer_no = customer_no.text
        
        currency = node.find('CURRENCY')
        if currency is not None:
            self.currency = currency.text
        
        for remark in node.findall('REMARKS'):
            if remark is not None:
                self.remarks.append(remark.text)
                
        h_udx = node.find('HEADER_UDX')
        if h_udx is not None:
            self.header_udx.createFromNode(h_udx)
            
        if delivery_date is not None:
            self.delivery_date.createFromNode(delivery_date)
        
        
        return OpenTransElement.createFromNode(self, node)
        
    def getOpenTrans(self, tag=None):
        res = super(OpenTransDispatchNotificationInfo,self).getOpenTrans('DISPATCHNOTIFICATION_INFO')
        
        order_id = SubElement(res,'ORDER_ID')
        order_id.text = self.order_id
        
        order_date = SubElement(res, 'ORDER_DATE')
        order_date.text = self.order_date
        
        res.append(self.parties.getOpenTrans())
        
        res.append(self.parties_reference.getOpenTrans())
        
        res.append(self.header_udx.getOpenTrans())
        
        
        return res
    
class OpenTransOrderResponseInfo(OpenTransElement):
    
    order_id = ""
    order_response_date = ""
    supplier_order_id = ""
    parties = OpenTransParties()
    delivery_date=OpenTransDeliveryDate()
    parties_reference = None
    header_udx = None
    customer_no = ""
    currency = ""
    remarks=[]
    
    def __init__(self):
        super(OpenTransOrderResponseInfo,self).__init__()
        self.parties = OpenTransParties()
        self.parties_reference = OpenTransOrderPartiesReference()
        self.header_udx = OpenTransHeaderUDX()
        self.delivery_date=OpenTransDeliveryDate()
        self.order_id=""
        
    def createFromNode(self, node):
        
        order_id = node.find('ORDER_ID')
        date = node.find('ORDERRESPONSE_DATE')
        supplier_order_id = node.find('SUPPLIER_ORDER_ID')
        delivery_date = node.find('DELIVERY_DATE')
        if order_id is not None:
            self.order_id = order_id.text
        if date is not None:
            self.order_response_date = date.text
        if supplier_order_id is not None:
            self.supplier_order_id = supplier_order_id.text
            
        parties = node.find('PARTIES')
        if parties is not None :
            self.parties.createFromNode(parties)
        
        part_ref = node.find('ORDER_PARTIES_REFERENCE')
        if part_ref is not None:
            self.parties_reference.createFromNode(part_ref)
            
        customer_no = node.find('CUSTOMER_NO')
        if customer_no is not None:
            self.customer_no = customer_no.text
        
        currency = node.find('CURRENCY')
        if currency is not None:
            self.currency = currency.text
        
        for remark in node.findall('REMARKS'):
            if remark is not None:
                self.remarks.append(remark.text)
                
        h_udx = node.find('HEADER_UDX')
        if h_udx is not None:
            self.header_udx.createFromNode(h_udx)
            
        if delivery_date is not None:
            self.delivery_date.createFromNode(delivery_date)
        
        
        return OpenTransElement.createFromNode(self, node)
        
    def getOpenTrans(self, tag=None):
        res = super(OpenTransOrderInfo,self).getOpenTrans('ORDER_INFO')
        
        order_id = SubElement(res,'ORDER_ID')
        order_id.text = self.order_id
        
        order_date = SubElement(res, 'ORDER_DATE')
        order_date.text = self.order_date
        
        res.append(self.parties.getOpenTrans())
        
        res.append(self.parties_reference.getOpenTrans())
        
        res.append(self.header_udx.getOpenTrans())
        
        
        return res
    
class OpenTransOrderHeader(OpenTransElement):
    
    control_info = OpenTransOrderControlInfo()
    order_info = OpenTransOrderInfo()
    
    def __init__(self):
        super(OpenTransOrderHeader,self).__init__()
        self.control_info = OpenTransOrderControlInfo()
        self.order_info = OpenTransOrderInfo()
        
    def getOpenTrans(self, tag=None):
        res = super(OpenTransOrderHeader,self).getOpenTrans('ORDER_HEADER')
        
        res.append(self.control_info.getOpenTrans())
        
        res.append(self.order_info.getOpenTrans())
        return res
    
class OpenTransDispatchNotificationHeader(OpenTransElement):
    
    control_info = OpenTransOrderControlInfo()
    dispatch_notification_info = OpenTransDispatchNotificationInfo()
    
    def __init__(self):
        super(OpenTransDispatchNotificationHeader,self).__init__()
        self.control_info = OpenTransOrderControlInfo()
        self.dispatch_notification_info = OpenTransDispatchNotificationInfo()
        
    def createFromNode(self, node):
        info = node.find('CONTROL_INFO')
        dispatch_info=node.find('DISPATCHNOTIFICATION_INFO')
        if info is not None:
            self.control_info.createFromNode(info)
        if dispatch_info is not None :
            self.dispatch_notification_info.createFromNode(dispatch_info)
        
        return OpenTransElement.createFromNode(self, node)
        
    def getOpenTrans(self, tag=None):
        res = super(OpenTransDispatchNotificationHeader,self).getOpenTrans('DISPATCHNOTIFICATION_HEADER')
        
        res.append(self.control_info.getOpenTrans())
        
        res.append(self.dispatch_notification_info.getOpenTrans())
        return res    
    
class OpenTransOrderResponseHeader(OpenTransElement):
    
    control_info = OpenTransOrderControlInfo()
    order_response_info = OpenTransOrderResponseInfo()
    
    def __init__(self):
        super(OpenTransOrderResponseHeader,self).__init__()
        self.control_info = OpenTransOrderControlInfo()
        self.order_response_info = OpenTransOrderResponseInfo()
        
    def createFromNode(self, node):
        info = node.find('CONTROL_INFO')
        resp_info=node.find('ORDERRESPONSE_INFO')
        if info is not None:
            self.control_info.createFromNode(info)
        if resp_info is not None :
            self.order_response_info.createFromNode(resp_info)
        
        return OpenTransElement.createFromNode(self, node)
        
    def getOpenTrans(self, tag=None):
        res = super(OpenTransOrderResponseHeader,self).getOpenTrans('ORDER_HEADER')
        
        res.append(self.control_info.getOpenTrans())
        
        res.append(self.order_response_info.getOpenTrans())
        return res    
    
class OpenTransProduct(OpenTransElement):
    
    supplier_pid = None
    description_short = None
    type="supplier_specific"
    
    def __init__(self):
        super(OpenTransProduct,self).__init__()
        self.supplier_pid=None
        self.description_short=None
        
    def createFromNode(self, node):
        supplier_pid = node.find('SUPPLIER_PID')
        description_short = node.find('DESCRIPTION_SHORT')
        
        if supplier_pid is not None:
            self.supplier_pid = supplier_pid.text
            if supplier_pid.attrib.has_key('type'):
                self.type = supplier_pid.attrib['type']
            
        if description_short is not None:
            self.description_short = description_short.text
            
        return OpenTransElement.createFromNode(self, node)
    
    def getOpenTrans(self):
        res=super(OpenTransProduct,self).getOpenTrans('PRODUCT_ID')
        
        supplier = SubElement(res, 'bmecat:SUPPLIER_PID')
        supplier.attrib['type']=self.type
        supplier.text = self.supplier_pid
        
        description = SubElement(res,'bmecat:DESCRIPTION_SHORT')
        description.text = self.description_short
        return res
    
class OpenTransAllowOCV(OpenTransElement):
    percentage_factor = 0.0
    
    def __init__(self):
        super(OpenTransAllowOCV,self).__init__()
        self.percentage_factor = 0.0
        
    def createFromNode(self, node):
        percentage_factor = node.find('AOC_PERCENTAGE_FACTOR')
        if percentage_factor is not None:
            self.percentage_factor = percentage_factor.text
            
    def getOpenTrans(self):
        res=super(OpenTransAllowOCV,self).getOpenTrans('ALLOW_OR_CHARGE_VALUE')
        
        percentage_factor = SubElement(res, 'AOC_PERCENTAGE_FACTOR')
        percentage_factor.text = self.percentage_factor
            
class OpenTransAllowOC(OpenTransElement):
    type = ""
    charge_type = ""
    charge_value = OpenTransAllowOCV
    
    def __init__(self):
        super(OpenTransAllowOC,self).__init__()
        self.type = ""
        self.charge_type = ""
        self.charge_value = OpenTransAllowOCV()
        
    def createFromNode(self, node):
        if node.tag == "ALLOW_OR_CHARGE" and node.attrib.has_key('type'):
            self.type = node.attrib['type']
            
        charge_type = node.find('ALLOW_OR_CHARGE_TYPE')
        if charge_type is not None :
            self.charge_type = charge_type.text
            
        charge_value = node.find('ALLOW_OR_CHARGE_VALUE')
        if charge_value is not None:
            self.charge_value.createFromNode(charge_value)
        
        return OpenTransElement.createFromNode(self, node)
    
    def getOpenTrans(self):
        res=super(OpenTransAllowOC,self).getOpenTrans('ALLOW_OR_CHARGE')
        
        if self.type and self.type != "":
            res.attrib['type'] = self.type
            
        if self.charge_type and self.charge_type != "":
            charge_type = SubElement(res, 'ALLOW_OR_CHARGE_TYPE')
            charge_type.text = self.charge_type
            
        res.append(self.charge_value.getOpenTrans())
    
class OpenTransAllowOCF(OpenTransElement):
    allow_or_charge = []
    total_amount = 0.0
    
    def __init__(self):
        super(OpenTransAllowOCF,self).__init__()
        self.allow_or_charge = []
        self.total_amount = 0.0
        
    def createFromNode(self, node):
        
        allow_or_charges = node.findall('ALLOW_OR_CHARGE')
        for allow_or_charge in allow_or_charges:
            if allow_or_charge is not None :
                aoc_item = OpenTransAllowOC()
                aoc_item.createFromNode(allow_or_charge)
                self.allow_or_charge.append(aoc_item)
            
        total_amount = node.find('ALLOW_OR_CHARGES_TOTAL_AMOUNT')
        if total_amount is not None:
            self.total_amount = total_amount.text
        
        return OpenTransElement.createFromNode(self, node)
    
class OpenTransTaxDetailsFix(OpenTransElement):
    type = ''
    
    def __init__(self):
        super(OpenTransTaxDetailsFix,self).__init__()
        self.type = ''
        
    def createFromNode(self, node):
            
        type = node.find('TAX_TYPE')
        if type is not None:
            self.type = type.text
        
        return OpenTransElement.createFromNode(self, node)
    

    def getOpenTrans(self):
        res=super(OpenTransTaxDetailsFix,self).getOpenTrans('TAX_DETAILS_FIX')
        
        type = SubElement(res,'TAX_TYPE')
        type.text=self.type
        
        return res
    
    
class OpenTransProductPriceFix(OpenTransElement):
    
    price_amount = 0.0
    price_quantity = 0.0
    allow_or_charge_fix=OpenTransAllowOCF
    tax_details_fix = OpenTransTaxDetailsFix
    
    def __init__(self):
        super(OpenTransProductPriceFix,self).__init__()
        self.price_amount = 0.0
        self.price_quantity = 0.0
        self.allow_or_charge_fix = OpenTransAllowOCF()
        self.tax_details_fix = OpenTransTaxDetailsFix()
    
    def createFromNode(self, node):
        
        price_amount = node.find('PRICE_AMOUNT')
        price_quantity = node.find('PRICE_QUANTITY')
        allow_or_charges_fix = node.find('ALLOW_OR_CHARGES_FIX')
        tax_details_fix = node.find('TAX_DETAILS_FIX')
        
        if price_amount is not None:
            self.price_amount = price_amount.text
            
        if price_quantity is not None:
            self.price_quantity = price_quantity.text
            
        if allow_or_charges_fix is not None:
            self.allow_or_charge_fix.createFromNode(allow_or_charges_fix)
            
        if tax_details_fix is not None:
            self.tax_details_fix.createFromNode(tax_details_fix)
            
        return OpenTransElement.createFromNode(self, node)
    
    def getOpenTrans(self):
        res=super(OpenTransProductPriceFix,self).getOpenTrans('PRODUCT_PRICE_FIX')
        
        line_item_id = SubElement(res,'LINE_ITEM_ID')
        line_item_id.text=self.line_item_id
        res.append(self.product_id.getOpenTrans())
        
        quantity = SubElement(res, 'QUANTITY')
        quantity.text = self.quantity
        
        order_unit = SubElement(res,'bmecat:ORDER_UNIT')
        order_unit.text = self.order_unit
        
        amount = SubElement(res, 'PRICE_LINE_AMOUNT')
        amount.text = self.price_line_amount
        
        return res
    
class OpenTransItemUDX(OpenTransElement):
    supplier_order_id=''
    shop_price_amount = 0.0
    shop_rebate_factor = 0.0

    def __init__(self):
        super(OpenTransItemUDX,self).__init__()
        self.supplier_order_id = ''
        self.shop_price_amount= 0.0
        self.shop_rebate_factor = 0.0
    
    def createFromNode(self, node):
        
        order_id = node.find('UDX_SUPPLIER_ORDER_ID')
        price_amount = node.find('UDX_SHOP_PRICE_AMOUNT')
        rebate_factor = node.find('UDX_SHOP_REBATE_FACTOR')
        
        if order_id is not None:
            self.supplier_order_id = order_id.text
        
        if price_amount is not None:
            self.shop_price_amount = float(price_amount.text)
            
        if rebate_factor is not None:
            self.shop_rebate_factor = float(rebate_factor.text)
            
            
    def getOpenTrans(self):
        res=super(OpenTransItemUDX,self).getOpenTrans('ITEM_UDX')
        
        order_id = SubElement(res,'UDX_SUPPLIER_ORDER_ID')
        order_id.text=self.supplier_order_id
        
        price_amount = SubElement(res,'UDX_SHOP_PRICE_AMOUNT')
        price_amount.text=self.shop_price_amount
        
        rebate_factor = SubElement(res,'UDX_SHOP_REBATE_FACTOR')
        rebate_factor.text=self.shop_rebate_factor       
        
        return res
    
    
class OpenTransShipmentPartiesReference(OpenTransElement):
    delivery_idref=''
    delivery_type = ''
    
    def __init__(self):
        super(OpenTransShipmentPartiesReference,self).__init__()
        self.delivery_idref = ''
        self.delivery_type= ''
    
    def createFromNode(self, node):
        
        id_ref = node.find('DELIVERY_IDREF')
        
        if id_ref is not None:
            self.delivery_idref = id_ref.text
            if id_ref.attrib.has_key('type'):
                self.delivery_type = id_ref.attrib('type')
            
            
    def getOpenTrans(self):
        res=super(OpenTransShipmentPartiesReference,self).getOpenTrans('SHIPMENT_PARTIES_REFERENCE')
        
        id_ref = SubElement(res,'DELIVERY_IDREF')
        id_ref.text=self.delivery_idref
        if self.delivery_type:
            id_ref.attrib['type'] = self.delivery_type
        
        return res
    
class OpenTransOrderReference(OpenTransElement):
    order_id=''
    line_item_id=''
    
    def __init__(self):
        super(OpenTransOrderReference,self).__init__()
        self.order_id = ''
        self.line_item_id= ''
    
    def createFromNode(self, node):
        
        order_id = node.find('ORDER_ID')
        line_item_id = node.find('LINE_ITEM_ID')
        
        
        if order_id is not None:
            self.order_id = order_id.text
            
        if line_item_id is not None:
            self.line_item_id = line_item_id.text
            
    def getOpenTrans(self):
        res=super(OpenTransOrderReference,self).getOpenTrans('ORDER_REFERENCE')
        
        order_id = SubElement(res,'ORDER_ID')
        order_id.text=self.order_id
        
        line_item_id = SubElement(res,'LINE_ITEM_ID')
        line_item_id.text=self.line_item_id
        
        return res
       
       
    
    
class OpenTransDispatchNotificationItem(OpenTransElement):
    
    line_item_id = None
    product_id = OpenTransProduct
    product_price_fix = OpenTransProductPriceFix
    quantity = 0.0
    order_unit = None
    price_line_amount = 0.0
    order_reference = OpenTransOrderReference
    shipment_parties_reference= OpenTransShipmentPartiesReference
    item_udx = OpenTransItemUDX
    shop_price_amount=0.0
    shop_rebate_factor = 0.0
    
    def __init__(self):
        super(OpenTransDispatchNotificationItem,self).__init__()
        self.product_id = OpenTransProduct()
        self.line_item_id = None
        self.product_price_fix=OpenTransProductPriceFix()
        self.order_unit=None
        self.price_line_amount = 0.0
        self.quantity = 0.0
        self.shop_price_amount = 0.0
        self.shop_rebate_factor = 0.0
        self.delivery_date=OpenTransDeliveryDate()
        self.item_udx = OpenTransItemUDX()
        self.order_reference = None
    
    def createFromNode(self, node):
        
        item_id = node.find('LINE_ITEM_ID')
        quantity = node.find('QUANTITY')
        order_unit = node.find('ORDER_UNIT')
        price_line_amount = node.find('PRICE_LINE_AMOUNT')
        shop_price_amount = node.find('SHOP_PRICE_AMOUNT')
        shop_rebate_factor = node.find('SHOP_REBATE_FACTOR')
        product_id = node.find('PRODUCT_ID')
        product_price_fix = node.find('PRODUCT_PRICE_FIX')
        delivery_date = node.find('DELIVERY_DATE')
        item_udx = node.find('ITEM_UDX')
        order_reference = node.find('ORDER_REFERENCE')
        
        if order_reference is not None:
            self.order_reference = OpenTransOrderReference()
            self.order_reference.createFromNode(order_reference)
        
        if item_id is not None:
            self.line_item_id = item_id.text
            
        if quantity is not None:
            self.quantity = quantity.text
            
        if price_line_amount is not None:
            self.price_line_amount = price_line_amount.text
            
        if shop_price_amount is not None:
            self.shop_price_amount = shop_price_amount.text
            
        if shop_rebate_factor is not None:
            self.shop_rebate_factor = shop_rebate_factor.text
        
        if order_unit is not None:
            self.order_unit = order_unit.text
            
        if product_id is not None:
            self.product_id.createFromNode(product_id)
        
        if product_price_fix is not None:
            self.product_price_fix.createFromNode(product_price_fix)
            
        if delivery_date is not None:
            self.delivery_date.createFromNode(delivery_date)
            
        if item_udx is not None:
            self.item_udx.createFromNode(item_udx)
 
        return OpenTransElement.createFromNode(self, node)
    
    def getOpenTrans(self):
        res=super(OpenTransDispatchNotificationItem,self).getOpenTrans('DISPATCHNOTIFICATION_ITEM')
        
        line_item_id = SubElement(res,'LINE_ITEM_ID')
        line_item_id.text=self.line_item_id
        
        res.append(self.product_id.getOpenTrans())
        
        quantity = SubElement(res, 'QUANTITY')
        quantity.text = self.quantity
        
        order_unit = SubElement(res,'bmecat:ORDER_UNIT')
        order_unit.text = self.order_unit
        
        res.append(self.order_reference.getOpenTrans())
    
        res.append(self.product_price_fix.getOpenTrans())
        
        res.append(self.shipment_parties_reference.getOpenTrans())
        
        price_amount = SubElement(res, 'SHOP_PRICE_AMOUNT')
        price_amount.text = self.price_amount
        
        rebate_factor = SubElement(res, 'SHOP_REBATE_FACTOR')
        rebate_factor.text = self.rebate_factor

        amount = SubElement(res, 'PRICE_LINE_AMOUNT')
        amount.text = self.price_line_amount
        
        res.append(self.item_udx.getOpenTrans())
        
        return res
    
class OpenTransOrderResponseItem(OpenTransElement):
    
    line_item_id = None
    product_id = OpenTransProduct
    product_price_fix = OpenTransProductPriceFix
    quantity = 0.0
    order_unit = None
    price_line_amount = 0.0
    delivery_date=OpenTransDeliveryDate
    shop_price_amount=0.0
    shop_rebate_factor = 0.0
    
    def __init__(self):
        super(OpenTransOrderResponseItem,self).__init__()
        self.product_id = OpenTransProduct()
        self.line_item_id = None
        self.product_price_fix=OpenTransProductPriceFix()
        self.order_unit=None
        self.price_line_amount = 0.0
        self.quantity = 0.0
        self.shop_price_amount = 0.0
        self.shop_rebate_factor = 0.0
        self.delivery_date=OpenTransDeliveryDate()
    
    def createFromNode(self, node):
        
        item_id = node.find('LINE_ITEM_ID')
        quantity = node.find('QUANTITY')
        order_unit = node.find('ORDER_UNIT')
        price_line_amount = node.find('PRICE_LINE_AMOUNT')
        shop_price_amount = node.find('SHOP_PRICE_AMOUNT')
        shop_rebate_factor = node.find('SHOP_REBATE_FACTOR')
        product_id = node.find('PRODUCT_ID')
        product_price_fix = node.find('PRODUCT_PRICE_FIX')
        delivery_date = node.find('DELIVERY_DATE')
        
        if item_id is not None:
            self.line_item_id = item_id.text
            
        if quantity is not None:
            self.quantity = quantity.text
            
        if price_line_amount is not None:
            self.price_line_amount = price_line_amount.text
            
        if shop_price_amount is not None:
            self.shop_price_amount = shop_price_amount.text
            
        if shop_rebate_factor is not None:
            self.shop_rebate_factor = shop_rebate_factor.text
        
        if order_unit is not None:
            self.order_unit = order_unit.text
            
        if product_id is not None:
            self.product_id.createFromNode(product_id)
        
        if product_price_fix is not None:
            self.product_price_fix.createFromNode(product_price_fix)
            
        if delivery_date is not None:
            self.delivery_date.createFromNode(delivery_date)
 
        return OpenTransElement.createFromNode(self, node)
    
    def getOpenTrans(self):
        res=super(OpenTransOrderResponseItem,self).getOpenTrans('ORDER_ITEM')
        
        line_item_id = SubElement(res,'LINE_ITEM_ID')
        line_item_id.text=self.line_item_id
        res.append(self.product_id.getOpenTrans())
        
        quantity = SubElement(res, 'QUANTITY')
        quantity.text = self.quantity
        
        order_unit = SubElement(res,'bmecat:ORDER_UNIT')
        order_unit.text = self.order_unit
        
        amount = SubElement(res, 'PRICE_LINE_AMOUNT')
        amount.text = self.price_line_amount
        
        return res
    
class OpenTransOrderItem(OpenTransElement):
    
    line_item_id = None
    product_id = OpenTransProduct
    quantity = 0.0
    order_unit = None
    price_line_amount = 0.0
    
    def __init__(self):
        super(OpenTransOrderItem,self).__init__()
        self.product_id = OpenTransProduct()
        self.line_item_id = None
        self.product_id=OpenTransProduct()
        self.order_unit=None
        self.price_line_amount = 0.0
    
    
    def getOpenTrans(self):
        res=super(OpenTransOrderItem,self).getOpenTrans('ORDER_ITEM')
        
        line_item_id = SubElement(res,'LINE_ITEM_ID')
        line_item_id.text=self.line_item_id
        res.append(self.product_id.getOpenTrans())
        
        quantity = SubElement(res, 'QUANTITY')
        quantity.text = self.quantity
        
        order_unit = SubElement(res,'bmecat:ORDER_UNIT')
        order_unit.text = self.order_unit
        
        amount = SubElement(res, 'PRICE_LINE_AMOUNT')
        amount.text = self.price_line_amount
        
        return res
    

class OpenTransOrderItemList(OpenTransElement):
    
    order_items = []
    
    def __init__(self):
        super(OpenTransOrderItemList,self).__init__()
        self.order_items=[]
    
    def getOpenTrans(self, tag=None):
        
        res=super(OpenTransOrderItemList,self).getOpenTrans('ORDER_ITEM_LIST')
        
        for order_item in self.order_items:
            res.append(order_item.getOpenTrans())
        
        return res
    
    
class OpenTransDispatchNotificationItemList(OpenTransElement):
    
    items = []
    
    def __init__(self):
        super(OpenTransDispatchNotificationItemList,self).__init__()
        self.items=[]
        
    def createFromNode(self, node):
        
        for item in node.findall('DISPATCHNOTIFICATION_ITEM'):
            if item is not None:
                d_item = OpenTransDispatchNotificationItem()
                d_item.createFromNode(item)
                self.items.append(d_item)
        
        return OpenTransElement.createFromNode(self, node)
    
    def getOpenTrans(self, tag=None):
        
        res=super(OpenTransDispatchNotificationItemList,self).getOpenTrans('DISPATCHNOTIFICATION_ITEM_LIST')
        
        for item in self.items:
            res.append(item.getOpenTrans())
        
        return res
    
class OpenTransOrderResponseItemList(OpenTransElement):
    
    order_items = []
    
    def __init__(self):
        super(OpenTransOrderResponseItemList,self).__init__()
        self.order_items=[]
        
    def createFromNode(self, node):
        
        for item in node.findall('ORDERRESPONSE_ITEM'):
            if item is not None:
                o_item = OpenTransOrderResponseItem()
                o_item.createFromNode(item)
                self.order_items.append(o_item)
        
        return OpenTransElement.createFromNode(self, node)
    
    def getOpenTrans(self, tag=None):
        
        res=super(OpenTransOrderResponseItemList,self).getOpenTrans('ORDERRESPONSE_ITEM_LIST')
        
        for order_item in self.order_items:
            res.append(order_item.getOpenTrans())
        
        return res
    
class OpenTransDispatchNotificationSummary(OpenTransElement):
    total_item_num = 0.0
    
    def __init__(self):
        super(OpenTransDispatchNotificationSummary,self).__init__()
        self.total_item_num = 0.0
    
    def getOpenTrans(self, tag=None):
        res=super(OpenTransDispatchNotificationSummary,self).getOpenTrans('DISPATCHNOTIFICATION_SUMMARY')
        
        num = SubElement(res, 'TOTAL_ITEM_NUM')
        num.text = self.total_item_num
        
        return res
    
class OpenTransOrderSummary(OpenTransElement):
    total_item_num = 0.0
    total_amount = 0.0
    
    def __init__(self):
        super(OpenTransOrderSummary,self).__init__()
        self.total_amount = 0.0
        self.total_item_num = 0.0
    
    def getOpenTrans(self, tag=None):
        res=super(OpenTransOrderSummary,self).getOpenTrans('ORDER_SUMMARY')
        
        num = SubElement(res, 'TOTAL_ITEM_NUM')
        num.text = str(self.total_item_num)
        
        total = SubElement(res,'TOTAL_AMOUNT')
        total.text = str(self.total_amount)
        
        return res
    
class OpenTransDispatchNotification(OpenTransElement):
    
    VERSION = "2.1"
    TYPE = "standard"
    BMECAT = "http://www.bmecat.org/bmecat/2005"
    
    header = OpenTransDispatchNotificationHeader()
    item_list = OpenTransDispatchNotificationItemList()
    summary = OpenTransDispatchNotificationSummary()
    
    def __init__(self):
        super(OpenTransDispatchNotification,self).__init__()
        self.header = OpenTransDispatchNotificationHeader()
        self.item_list = OpenTransDispatchNotificationItemList()
        self.summary = OpenTransDispatchNotificationSummary()
        
    def createFromNode(self, node):
        header = node.find("DISPATCHNOTIFICATION_HEADER")
        if header is not None:
            self.header.createFromNode(header)
            
        list = node.find("DISPATCHNOTIFICATION_ITEM_LIST")
        if list is not None :
            self.item_list.createFromNode(list)
            
        summary = node.find("DISPATCHNOTIFICATION_SUMMARY")
        if summary is not None:
            self.summary.createFromNode(summary)
                        
        return OpenTransElement.createFromNode(self, node)
        
    def getOpenTrans(self, tag=None):
        res=super(OpenTransDispatchNotification,self).getOpenTrans('DISPATCHNOTIFICATION')
        res.attrib['type']=self.TYPE
        res.attrib["version"]=self.VERSION
        res.attrib["xmlns:bmecat"]=self.BMECAT
        
        res.append(self.header.getOpenTrans())
        
        res.append(self.item_list.getOpenTrans())
        
        res.append(self.summary.getOpenTrans())
        return res
    
class OpenTransOrder(OpenTransElement):
    
    VERSION = "2.1"
    TYPE = "express"
    BMECAT = "http://www.bmecat.org/bmecat/2005"
    
    order_header = OpenTransOrderHeader()
    item_list = OpenTransOrderItemList()
    summary = OpenTransOrderSummary()
    
    def __init__(self):
        super(OpenTransOrder,self).__init__()
        self.order_header = OpenTransOrderHeader()
        self.item_list = OpenTransOrderItemList()
        self.summary = OpenTransOrderSummary()
        
    def getOpenTrans(self, tag=None):
        res=super(OpenTransOrder,self).getOpenTrans('ORDER')
        res.attrib['type']=self.TYPE
        res.attrib["version"]=self.VERSION
        res.attrib["xmlns:bmecat"]=self.BMECAT
        
        res.append(self.order_header.getOpenTrans())
        
        res.append(self.item_list.getOpenTrans())
        
        res.append(self.summary.getOpenTrans())
        return res
    
class OpenTransOrderResponse(OpenTransElement):
    
    VERSION = "2.1"
    TYPE = "express"
    BMECAT = "http://www.bmecat.org/bmecat/2005"
    
    order_response_header = OpenTransOrderResponseHeader()
    item_list = OpenTransOrderResponseItemList()
    
    def __init__(self):
        super(OpenTransOrderResponse,self).__init__()
        self.order_response_header = OpenTransOrderResponseHeader()
        self.item_list = OpenTransOrderResponseItemList()
        
    def createFromNode(self, node):
        header = node.find("ORDERRESPONSE_HEADER")
        if header is not None:
            self.order_response_header.createFromNode(header)
            
        list = node.find("ORDERRESPONSE_ITEM_LIST")
        if list is not None :
            self.item_list.createFromNode(list)
                        
        return OpenTransElement.createFromNode(self, node)
        
    def getOpenTrans(self, tag=None):
        res=super(OpenTransOrder,self).getOpenTrans('ORDERRESPONSE')
        res.attrib['type']=self.TYPE
        res.attrib["version"]=self.VERSION
        res.attrib["xmlns:bmecat"]=self.BMECAT
        
        res.append(self.order_header.getOpenTrans())
        
        res.append(self.item_list.getOpenTrans())
        return res
    
class OpenTransDocument():
    
    VERSION = "2.1"
    TYPE = "express"
    BMECAT = "http://www.bmecat.org/bmecat/2005"
    
    
    element = OpenTransElement
    
    def createDocumentFromXML(self,xml):
        
        tree = ElementTree(fromstring(xml))
        
        if tree._root.tag == 'ORDERRESPONSE' :
            OrderResponse = OpenTransOrderResponse()
            if OrderResponse.createFromNode(tree):
                self.element=OrderResponse
        elif tree._root.tag == 'DISPATCHNOTIFICATION':
            DispatchNotification = OpenTransDispatchNotification()
            if DispatchNotification.createFromNode(tree):
                self.element=DispatchNotification
        
      
            
            
        
    
    def createDocument(self):
        order = self._createOrder()
        header = self._createHeader()
        order_info = self._createOrderInfo()
        
        header.append(order_info)
        order.append(header)
        
    def _createOrder(self):
        order = Element('ORDER')
        order.attrib["version"] = self.VERSION
        order.attrib["type"] = self.TYPE #Choose the type of delivery : standard, express, release, consignment
        order.attrib["xmlns:bmecat"] = self.BMECAT
        
        return order
        
        
    
    def _createHeader(self):
        header = Element('ORDER_HEADER')
        
        control_info = SubElement(header, 'CONTROL_INFO')
        generation_date = SubElement(control_info, 'GENERATION_DATE')
        generation_date.text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+01:00")
        
        return header
        
        
    def _createOrderInfo(self):
        ###ORDERINFO
        order_info = Element('ORDER_INFO')
        
        
        return order_info
OpenTransDocument()
        

class OpenTransInterface(models.AbstractModel):
    _name='opentrans.interface'
    
    @api.model
    def createOpenTransDocument(self,order):
        return OpenTransDocument()
    
    @api.model
    def createFromOpenTransDocument(self,document):
        oDocument = OpenTransDocument()
        
        oDocument.createDocumentFromXML(document)
        return
    
    @api.model
    def createFromOpenTransXML(self,xml):
        oDocument = OpenTransDocument()
        
        oDocument.createDocumentFromXML(xml)
        return oDocument