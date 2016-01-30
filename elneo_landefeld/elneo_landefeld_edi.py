# -*- encoding: utf-8 -*- 
from ftplib import FTP, error_perm
from datetime import datetime
from StringIO import *
import base64

from openerp import models, fields, api
from openerp.tools.safe_eval import safe_eval


class ResConfigEdiLandefeld(models.TransientModel):
    _inherit='res.config.settings'
    _name='edi.landefeld.config.settings'
    
    
    ftp_isPassive = fields.Boolean(string='Is Passive',default=False)
    ftp_port=fields.Integer(string='Port',default=21)
    ftp_host=fields.Char(string='Server Address')
    ftp_user=fields.Char(string='User')
    ftp_password=fields.Char(string='Password')
    
    ftp_import_dir=fields.Char(string='Import Directory')
    ftp_export_dir=fields.Char(string='Export Directory')
    
    ftp_history_dir=fields.Char(string='History Directory')
    
    
    route_dropshipping=fields.Many2one('stock.location.route',string='Landfeld Internet Order Dropshipping Route')
    
    
    
    
    @api.multi
    def set_route_dropshipping(self):
        
        self.env['ir.config_parameter'].set_param('elneo_landefeld.route_dropshipping',repr(self.route_dropshipping.id))
        
    
    @api.multi
    def get_default_route_dropshipping(self):
        res = {}
        route = safe_eval(self.env['ir.config_parameter'].get_param('elneo_landefeld.route_dropshipping','False'))
        if route:
            res.update({'route_dropshipping':route})
        
        return res
    
    @api.multi
    def get_default_ftp_isPassive(self):
        res = {}
        is_passive = safe_eval(self.env['ir.config_parameter'].get_param('elneo_landefeld.ftp_is_passive','False'))
        res.update({'ftp_isPassive':is_passive})
        
        return res
    
    @api.multi
    def set_ftp_isPassive(self):
        
        self.env['ir.config_parameter'].set_param('elneo_landefeld.ftp_is_passive',repr(self.ftp_isPassive))
        
    @api.multi
    def get_default_ftp_port(self):
        res = {}
        ftp_port = safe_eval(self.env['ir.config_parameter'].get_param('elneo_landefeld.ftp_port','False'))
        res.update({'ftp_port':ftp_port})
        
        return res
    
    @api.multi
    def set_ftp_port(self):
        
        self.env['ir.config_parameter'].set_param('elneo_landefeld.ftp_port',repr(self.ftp_port))
        
    @api.multi
    def get_default_ftp_host(self):
        res = {}
        ftp_host = self.env['ir.config_parameter'].get_param('elneo_landefeld.ftp_host','False')
        res.update({'ftp_host':ftp_host})
        
        return res
    
    @api.multi
    def set_ftp_host(self):
        
        self.env['ir.config_parameter'].set_param('elneo_landefeld.ftp_host',self.ftp_host)
        
    @api.multi
    def get_default_ftp_user(self):
        res = {}
        ftp_user = self.env['ir.config_parameter'].get_param('elneo_landefeld.ftp_user','False')
        res.update({'ftp_user':ftp_user})
        
        return res
    
    @api.multi
    def set_ftp_user(self):
        
        self.env['ir.config_parameter'].set_param('elneo_landefeld.ftp_user',self.ftp_user)
        
    @api.multi
    def get_default_ftp_password(self):
        res = {}
        ftp_password = self.env['ir.config_parameter'].get_param('elneo_landefeld.ftp_password','False')
        res.update({'ftp_password':ftp_password})
        
        return res
    
    @api.multi
    def set_ftp_password(self):
        
        self.env['ir.config_parameter'].set_param('elneo_landefeld.ftp_password',self.ftp_password)
        
    @api.multi
    def get_default_ftp_import_dir(self):
        res = {}
        ftp_import_dir = self.env['ir.config_parameter'].get_param('elneo_landefeld.ftp_import_dir','False')
        res.update({'ftp_import_dir':ftp_import_dir})
        
        return res
    
    @api.multi
    def set_ftp_import_dir(self):
        
        self.env['ir.config_parameter'].set_param('elneo_landefeld.ftp_import_dir',self.ftp_import_dir)
        
    @api.multi
    def get_default_ftp_export_dir(self):
        res = {}
        ftp_export_dir = self.env['ir.config_parameter'].get_param('elneo_landefeld.ftp_export_dir','False')
        res.update({'ftp_export_dir':ftp_export_dir})
        
        return res
    
    @api.multi
    def set_ftp_export_dir(self):
        
        self.env['ir.config_parameter'].set_param('elneo_landefeld.ftp_export_dir',self.ftp_export_dir)
        
    @api.multi
    def get_default_ftp_history_dir(self):
        res = {}
        ftp_history_dir = self.env['ir.config_parameter'].get_param('elneo_landefeld.ftp_history_dir','False')
        res.update({'ftp_history_dir':ftp_history_dir})
        
        return res
    
    @api.multi
    def set_ftp_history_dir(self):
        
        self.env['ir.config_parameter'].set_param('elneo_landefeld.ftp_history_dir',self.ftp_history_dir)
    
    
    
    
    
    
    '''
        dirname_old = '/ftp62360/out/old'               # remote directory of history
        dirname = '/ftp62360/out'               # remote directory to fetch from
        host = 'fw.landefeld.de'                # adresse du serveur FTP
        user = 'ftp62360'                       # votre identifiant
        password = 'HB579@int6'                 # votre mot de passe
        
    '''



class EDIProcessor(models.Model):
    _inherit='edi.processor'
    
    processor_type = fields.Selection(selection_add=[('landefeld','Landefeld')])
    
    @api.model
    def _create_history_dir(self,connection,ftp_history_dir):
        #create history folder

        dir_date_name = datetime.today().strftime("%y%m%d")
        old_dir_exist = False
        #connection.cwd(ftp_history_dir)
        for dir_date in connection.nlst(ftp_history_dir):
            if dir_date == ftp_history_dir+'/'+dir_date_name:
                old_dir_exist = True
        if not old_dir_exist:
            connection.mkd(ftp_history_dir+'/'+dir_date_name)
        
        return dir_date_name
        
    @api.one
    @api.returns('edi.message')
    def _transfer_files(self,file_type='ORDER',connection=None,ftp_import_dir='',ftp_history_dir='',date_dir=''):
        transferFileList = connection.nlst(ftp_import_dir)
        edi_messages = self.env['edi.message']
        for transfertfile in transferFileList:
            self.edi_log('info','type='+unicode(type)+' transfertfile='+unicode(transfertfile)+' lower='+unicode(transfertfile.lower()))
            
            if ((file_type=='ORDER' and 'orderresponse_' in transfertfile.lower()) or (file_type=='DISPATCH' and 'dispatchnotification_' in transfertfile.lower())):
                stream = StringIO()
                connection.retrbinary('RETR ' + transfertfile, stream.write)
                message_type = self.message_type_ids.filtered(lambda r:r.usage == 'incoming')
                message_type.ensure_one()
                edi_message = self.env['edi.message'].create(
                                                   {'type':message_type.id,
                                                    'state':'draft', 
                                                    })

                edi_messages+=edi_message
                
                
                filename_template = (file_type == 'ORDER') and 'orderresponses-%s-%s.xml' or 'dispatchnote-%s-%s.xml'
                filename = filename_template % (datetime.today().strftime("%Y-%m-%d"),edi_message.name)
                
                self.env['ir.attachment'].create({
                                                  'res_id' : edi_message.id,
                                                  'res_model' : 'edi.message',
                                                  'name' : filename,
                                                  'datas_fname': filename,
                                                  'datas' : base64.encodestring(stream.getvalue())
                                                  }
                                                 )
                
                self._move_files(connection, transfertfile, ftp_history_dir,date_dir)
                
        return edi_messages
    
    @api.one
    def _move_files(self,connection, transfertfile,ftp_history_dir,date_dir):
        file_name = transfertfile.split("/").pop()
        file_dest = ftp_history_dir+'/'+date_dir+'/'+file_name
        try:
            connection.rename(transfertfile, file_dest)
        except error_perm:                    
            #if an error occure and file exist on destination delete it
            for exist_file in connection.nlst(ftp_history_dir+'/'+dir):
                if exist_file == file_dest:
                    connection.delete(file_dest)
                    connection.rename(transfertfile, file_dest)
        except Exception:
            pass
        
        return True
               
        
    
    @api.one
    @api.returns('edi.message')
    def _import_FTP(self,file_type='ORDER'):
        ftp_isPassive = self.env['ir.config_parameter'].get_param('elneo_landefeld.ftp_isPassive','False')
        if self.env['ir.config_parameter'].get_param('elneo_landefeld.ftp_isPassive','False') == 'True':
            ftp_isPassive=True
        else:
            ftp_isPassive=False
        ftp_port = int(self.env['ir.config_parameter'].get_param('elneo_landefeld.ftp_port','False'))
        ftp_host = str(self.env['ir.config_parameter'].get_param('elneo_landefeld.ftp_host','False'))
        ftp_user = str(self.env['ir.config_parameter'].get_param('elneo_landefeld.ftp_user','False'))
        ftp_password = str(self.env['ir.config_parameter'].get_param('elneo_landefeld.ftp_password','False'))
        ftp_import_dir = self.env['ir.config_parameter'].get_param('elneo_landefeld.ftp_import_dir','False')
        ftp_history_dir = self.env['ir.config_parameter'].get_param('elneo_landefeld.ftp_history_dir','False')
        
        
        connection = FTP()
        
        edi_messages = self.env['edi.message']
        self.edi_log(log_type='info',log='Begin FTP Import')
        try:
            
            
            connection.set_debuglevel(2)
            connection.set_pasv(ftp_isPassive)
            connection.connect(ftp_host,ftp_port,3)
            connection.login(ftp_user,ftp_password)
            
             
            history_dir = self._create_history_dir(connection,ftp_history_dir)
            
            if dir :
                self.edi_log('info','History directory created')
            
            edi_messages = self._transfer_files(file_type,connection,ftp_import_dir,ftp_history_dir,history_dir)
            
            self.edi_log(log_type='info',log='End FTP Import')
            
        except Exception,e:
            self.edi_log(log_type='error',log=e.message)
            
        finally:
            #Close ftp connection
            connection.quit()
            
        
        return edi_messages
        
        
    
    @api.one
    def _import_landefeld(self):
        edi_messages = self.env['edi.message']
        edi_messages += self._import_FTP(file_type='ORDER')
        edi_messages += self._import_FTP(file_type='DISPATCH')
        
        edi_messages.action_confirm()
        
        return True
        
    
    @api.model
    def import_messages(self):
        for processor in self.search([('processor_type','in',['landefeld']),('message_type_ids.usage','in',['incoming']),('active','=',True)],order='priority'):
            if not processor._import_landefeld():
                return False
           
            
        return True