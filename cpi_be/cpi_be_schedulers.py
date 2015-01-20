
from datetime import datetime
import urllib2
from xml.dom.minidom import parse, parseString
from openerp import models, api

class scheduler_check_landefeld(models.Model):
    _name = 'scheduler.cpi_be'
    
    @api.model
    @api.multi
    def import_cpi_be_all(self):
        u1=urllib2.urlopen('http://ng3.economie.fgov.be/ni/indicators/XML/ConsumerPriceIndices.xml')
        dom=parse(u1)
        
        cpi_be_entry_pool = self.env['cpi.be.entry']
        cpi_be_type_pool = self.env['cpi.be.type']
        
        #cpi_be_entry_pool = self.pool.get("cpi.be.entry")
        #cpi_be_type_pool = self.pool.get("cpi.be.type")
        
        if dom.childNodes:
            for node_type in dom.childNodes[0].childNodes:
                if node_type.nodeType == node_type.ELEMENT_NODE and node_type.nodeName == 'INDEX':
                    
                   
                    year = False
                    month = False
                    value = False
                    
                    #BROWSE TYPE AND FIND IT (OR CREATE IT IF NOT EXIST)                    
                    type_name = node_type.getAttribute("BASE")
                    type_description = node_type.getAttribute("DESCRIPTION")
                    type_ids = cpi_be_type_pool.search([('name','=',type_name)])
                    if not type_ids:
                        type = cpi_be_type_pool.create({'name':type_name, 'description':type_description})
                    else:
                        type = type_ids[0]
                    
                    #BROWSE YEARS
                    for node_year in node_type.childNodes:
                        if node_year.nodeType == node_year.ELEMENT_NODE and node_year.nodeName == 'YEAR':
                            year = int(node_year.getAttribute("NAME"))
                            for values_node in node_year.childNodes:
                                if values_node.nodeType == values_node.ELEMENT_NODE and values_node.nodeName == 'VALUES':
                                    #BROWSE MONTHS
                                    for entry_node in values_node.childNodes:
                                        if entry_node.nodeType == entry_node.ELEMENT_NODE and entry_node.nodeName == 'ENTRY':
                                            month = entry_node.getAttribute("MONTH")
                                            if entry_node.childNodes and entry_node.childNodes[0].nodeType == entry_node.childNodes[0].TEXT_NODE:
                                                value = float(entry_node.childNodes[0].data)
                                            
                                            #CREATE OR UPDATE ENTRY
                                            if type and year and month and value:
                                                entries = cpi_be_entry_pool.search([('type_id','=',type.id),('year','=',year),('month','=',month)])
                                                if entries:
                                                    entries.write({'value':value})
                                                else:
                                                    cpi_be_entry_pool.create({'type_id':type.id, 'year':year, 'month':month, 'value':value})
                    
                
        return True
    
scheduler_check_landefeld()