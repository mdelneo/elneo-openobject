import base64
import dateutil.parser

from ftplib import FTP, error_perm
from xml.etree.ElementTree import fromstring, ElementTree
from datetime import datetime
from StringIO import *
import traceback
import os
from openerp import models

class elneo_update_landefeld_prices_wizard(models.TransientModel):
    _name = 'elneo.update.landefeld.prices.wizard'
    
    def retrieve_landefeld_pricelist(self, cr, uid, ids=False, context=None):
        if '10.0.0.117' in os.popen("cat /etc/network/interfaces | grep address","r").read()[8:]:
            self.import_from_landefeld(cr, uid, ids, context)
        return True
    
    def import_from_landefeld(self, cr, uid, ids, context):
        #browse FTP
        isPassive = False
        port = 21
        dirname_old = '/ftp62360/out/old_pricemodification'               # remote directory of history
        dirname = '/ftp62360/out'               # remote directory to fetch from
        host = 'fw.landefeld.de'                # adresse du serveur FTP
        user = 'ftp62360'                       # votre identifiant
        password = 'HB579@int6'                 # votre mot de passe
        
        price_update_pool = self.pool.get("elneo.supplier.price.update")
        price_update_ids = []


        connection=FTP()
        try:           
            
            connection.set_debuglevel(2)
            connection.set_pasv(isPassive)
            connection.connect(host,port,3)
            connection.login(user,password)
                        
            
            folder_created = False
            
            #retreive file
            transferFileList = connection.nlst(dirname)
            for transfertfile in transferFileList:
                
                if not folder_created:
                    #create history folder
                    dir_date_name = datetime.today().strftime("%y%m%d")
                    old_dir_exist = False
                    for dir_date in connection.nlst(dirname_old):
                        if dir_date == dirname_old+'/'+dir_date_name:
                            old_dir_exist = True
                    if not old_dir_exist:
                        connection.mkd(dirname_old+'/'+dir_date_name)
                    folder_created = True
                
                if 'pricemodifications-62360' in transfertfile.lower():
                    
                    #access to csv-file
                    stream = StringIO()
                    connection.retrbinary('RETR ' + transfertfile, stream.write)
                    
                    price_update_id = price_update_pool.create(cr, uid, {
                        'type':'landefeld', 
                        'supplier_id':4509
                        }, context)
                        
                    price_update_ids.append(price_update_id)
                    
                    #create attachment 
                    filename_template = 'priceupdate-%s-%s.csv'
                    filename = filename_template % (datetime.today().strftime("%Y%m%d"),unicode(price_update_id).zfill(2)[-2:],)
                    
                    #Put it in the import_file column
                    #self.pool.get('elneo.supplier.price.update').write(cr,uid,price_update_id,{'pricelist_file':base64.encodestring(stream.getvalue())})
                    #Put it in the attachment
                    self.pool.get('ir.attachment').create(cr, uid, {
                                                                    'res_id': price_update_id,
                                                                    'res_model': 'elneo.supplier.price.update',
                                                                    'name': filename,
                                                                    'datas': base64.encodestring(stream.getvalue()),
                                                                    }, context=context)
                    
                    # Move file on remote FTP                    
                    file_dest = dirname_old+'/'+dir_date_name+'/'+filename
                    try:
                        connection.rename(transfertfile, file_dest)
                    except error_perm:                    
                        #if an error occure and file exist on destination delete it
                        for exist_file in connection.nlst(dirname_old+'/'+dir_date_name):
                            if exist_file == file_dest:
                                connection.delete(file_dest)
                                connection.rename(transfertfile, file_dest)
                    except Exception:
                        pass
                        
        finally:
            #Close ftp connection            
            connection.quit()
        
        # Make commit if cursor for import and compute is not the same as here
        cr.commit()    
        
        #execute functions
        if not context:
            context = {}
        context['no_thread'] = True
        
        price_update_pool._import_csv(cr,uid,price_update_ids,context)
        price_update_pool.action_computing(cr, uid, price_update_ids, context)
        
        #check increase
        for price_update in price_update_pool.browse(cr, uid, price_update_ids, context):
            if price_update.state == 'computed' and price_update.increase_price and price_update.increase_price < 5.:
                price_update.action_updating_purchase_prices(cr, uid, price_update_ids, context)
                price_update.action_updating(cr, uid, price_update_ids, context)

        return {'type': 'ir.actions.act_window_close'}
    
elneo_update_landefeld_prices_wizard()

