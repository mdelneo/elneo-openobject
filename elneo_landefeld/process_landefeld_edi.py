
from openerp import models, api, _

import base64


class EDIProcessor(models.Model):
    _name='edi.processor'
    _inherit=['edi.processor','opentrans.interface']
    
    @api.model
    def _process(self,messages):
        for message in messages.filtered(lambda r:r.type.processor.id==self.id and r.state=='confirmed'):
            attachments = self.env['ir.attachment'].search([('res_model','=','edi.message'),('res_id','=',message.id)])
            for attachment in attachments:
                document = self.createFromOpenTransXML(base64.decodestring(attachment.datas))
                
                wizard = self.env['edi.processor.landefeld'].create({'edi_message':message.id,'edi_processor':self.id})
                
                wizard._process_landefeld_document(document)
        
                if wizard.warning_message:
                    message.message_post( 
                        body = _("A warning has occured during Landefeld EDI document processing.") + " <b><a href='#id=" + str(message.id) + "&view_type=form&model=edi.message'> " + message.name + " </a></b><br/><br/>" + wizard.warning_message,
                        type = 'mail',
                        subtype = "mail.mt_comment",
                        model = 'edi.message', res_id = message.id, 
                        partner_ids = [self.send_warning_users])
                    
                if wizard.error_message:
                    message.message_post( 
                        body = _("An error has occured during Landefeld EDI document processing.") + " <b><a href='#id=" + str(message.id) + "&view_type=form&model=edi.message'> " + message.name + " </a></b><br/><br/>" + wizard.error_message,
                        type = 'mail',
                        subtype = "mail.mt_comment",
                        model = 'edi.message', res_id = message.id, 
                        partner_ids = [self.send_error_users])
                    
                if wizard.state in ['ok','warning']:
                    message.state = 'done'
                elif wizard.state == 'error':
                    message.state = 'error'
             
            
            
    
        return super(EDIProcessor,self)._process(messages)        