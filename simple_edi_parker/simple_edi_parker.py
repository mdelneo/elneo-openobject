from openerp import models, api,registry
import unicodedata
from datetime import date
from ftplib import FTP, error_perm
from datetime import datetime
from StringIO import *
import base64


class purchase_order(models.Model):
    _inherit = 'purchase.order'    
    
    @api.one
    def send_simple_edi_parker(self):
        edi = self.get_edi_parker()
        
        stream = StringIO()
        stream.write(edi[0])

        filename = 'TNF55850.txt'
        
        attachment = self.env['ir.attachment'].create({
          'res_id' : self.id,
          'res_model' : 'purchase.order',
          'name' : filename,
          'datas_fname': filename,
          'datas' : base64.encodestring(stream.getvalue())
          }
         )
        
        email_from = self.env['res.users'].browse(self._uid).partner_id.email
        servers = self.env['ir.mail_server'].search([('smtp_user','=',email_from)])
        
        mail = self.env['mail.mail'].create({
                'reply_to':None,
                'mail_server_id':servers[0].id,
                'email_from':email_from,
                'author_id':self.env['res.users'].browse(self._uid).partner_id.id,
                'email_to':'ECOMDATA@parker.com',
                'email_cc':'Simple_EDI_Belgium@parker.com, nbral@parker.com',
                'subject':'TNF55850 Order '+str(self.name), 
                'type':'email',
                'attachment_ids':[(4,attachment.id)]
        })
        
        
    
    def edi_format_field(self, value, length):
        """Returns a string with the length specified, composed by value parameter (truncated if it must be), completed by spaces
        @param self: The object pointer     
        @param value: field to format
        @param length : field length
        """
        if value is None:
            res = ""
        else:        
            res  = unicodedata.normalize('NFKD', unicode(value)).encode('ascii','replace')[:length] 
        res = res.ljust(length, " ")
        return res
    
    def edi_format_date(self, date_p):
        """Format the date passed in parameter for EDI Parker format : month/day/year  
        @param self: The object pointer
        @param date_p: date to format     
        """
        date_split = date_p[0:10].split("-")
        d = date(int(date_split[0]),int(date_split[1]),int(date_split[2]))
        return d.strftime("%m/%d/%y")
    
    @api.one
    def get_edi_parker(self):
        edi = ''
        
        #EDI specification for Parker : each Technofluid departments must have an EDI code.
        EDI_DPTS_CODES = {
                            'MAIN-A' : "0023",
                            'MAIN-W' : "0026",
                            'COMP-A' : "0022",
                            'COMP-W' : "0025",
                            'INST-A' : "0024",
                            #'INST_W' : "",
                            'PNEU-A' : "0020",
                            'PNEU-W' : "0021",
                            'HYDR-A' : "0028",
                            'HYDR-W' : "0027",
        }
        
        #Find the department code in accordance with user logged and EDI_DPTS_CODES
        dpt = self.env['res.users'].browse(self._uid).default_section_id
        if dpt and EDI_DPTS_CODES.has_key(dpt.code):
            dpt_code = EDI_DPTS_CODES[dpt.code]
        else:
            dpt_code = "    "
            
        #For each purchase order (for a report, it must be unique), write the EDI lines
        order_date = self.date_order
        order_code = self.name
        
        line_number = 0            
        #For each line of the purchase order, write the corresponding EDI string.
        for line in self.order_line:
            if line.product_id:
                line_number += 1
                
                line_product_saler_ref = None
                
                #find the supplier info line corresponding with the order supplier and the product of the order line
                for supplier_info in line.product_id.product_tmpl_id.seller_ids:
                    if supplier_info.name.id == self.partner_id.id:
                        if supplier_info.product_code:
                            line_product_saler_ref = supplier_info.product_code
                        else:
                            line_product_saler_ref = line.product_id.default_code
                        
                if line_product_saler_ref == None:
                    raise Exception(_('%s has not supplier %s')%(line.product_id.default_code, self.partner_id.name)) #TODO : debug to know why exception is not catched
                    
                line_product_code = line.product_id.default_code
                line_qty = str(line.product_qty)
                line_date_planned = line.date_planned
                line_product_name = line.product_id.name
                
                edi_order_line = self.edi_format_field(dpt_code,4)
                edi_order_line += self.edi_format_field(order_code,8)
                edi_order_line += unicode("    ")
                edi_order_line += self.edi_format_field(unicode(line_number),4)
                
                edi_order_line += self.edi_format_field(line_product_code,15)
                
                edi_order_line += unicode("    ")
                
                #format line_qty without 0 after comma, and with precision of 3
                #edi_order_line += self.edi_format_field("{0:g}".format(line_qty),13) #don't works in python version 2.5, only in 2.7
                if int(unicode(line_qty).split(".")[1]) == 0:
                    edi_order_line += self.edi_format_field(unicode(line_qty).split(".")[0],13) 
                else:
                    edi_order_line += self.edi_format_field(unicode(line_qty),13)
                    
                edi_order_line += self.edi_format_date(line_date_planned)
                edi_order_line += self.edi_format_date(order_date)
                edi_order_line += self.edi_format_field(line_product_saler_ref,25)
                edi_order_line += self.edi_format_field(line_product_name,40)
                
                #add a number for delivery : 8 for express delivery. 6 for Replenishment at position 372
                edi_order_line += ''.ljust(238, ' ')
                edi_order_line += '8'
                ''' uncomment following lines when parker delivery issue is resolved
                if self.sale_orders:
                    edi_order_line += '8'
                else:
                    edi_order_line += '6'
                '''
                
                '''edi_order_line = self.edi_format_field(edi_order_line,256) #Format line to 256 characters
                edi_order_line += unicode("\r\n")
                res[self.id] += unicodedata.normalize('NFKD', edi_order_line).encode('ascii','replace')'''
                edi_order_line = (edi_order_line[:372]).ljust(372, " ")
                
                edi_order_line+="\r\n"
        
                edi += edi_order_line
                
        return edi