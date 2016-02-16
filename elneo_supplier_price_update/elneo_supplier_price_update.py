from datetime import datetime, timedelta
import threading
import base64

import time
import shlex,subprocess
import os
import sys
from openerp import models,fields,api, pooler, netsvc, sql_db, _
from openerp.exceptions import Warning
import logging

_logger = logging.getLogger(__name__)

class product_group(models.Model):
    _inherit = 'product.group'
    
    category_id = fields.Many2one('product.category', string="Equivalent category")


class elneo_supplier_price_update(models.Model):
    _name='elneo.supplier.price.update'
    
    def copy(self, cr, uid, id, default={}, context=None):
        if context is None:
            context = {}
        default.update({
            'state':'draft',
        })
      
        return super(elneo_supplier_price_update, self).copy(cr, uid, id, default, context)
    
    
    @api.depends('state')
    def _get_increase_percent(self,cr,uid,ids,name,args,context=None):
        res={}
        
        for update in self.pool.get('elneo.supplier.price.update').browse(cr,uid,ids,context=context):
            i=0
            tmp=0.0
            for line in update.lines_sold:
                tmp=tmp + line.net_price_difference
                i+=1
            
            if i != 0:
                res[update.id] = tmp / i
        
        return res
          
    state = fields.Selection([('draft','Draft'),('computing','Computing'),('computing_error','Computing Error'),('computed','Computed'),('updating_pps','Updating Purchase Prices'),('updated_pps','Purchase Prices Updated'),('updating','Updating'),('updating_error','Updating Error'),('done','Done'),('cancel','Canceled')],string='State',readonly=True, default='draft')
    code = fields.Char('Code',size=30,help='The Import Code',readonly=True)
    supplier_id = fields.Many2one('res.partner',string="Supplier",domain=[('supplier','=','True')],required=True)
    date = fields.Datetime('Date',help='Date of Import', default=lambda *a : datetime.today().strftime('%Y-%m-%d %H:%M:%S'))
    type = fields.Selection([('landefeld','Landefeld'),('elneo_standard','Standard')],string="Type",required=True,help='The type of input will determine which kind of file structure can be imported.')
    save_in_sale_price_fixed = fields.Boolean('Save in Sale Price')
    complete_list_price = fields.Boolean('Complete Price List')
    pricelist_file = fields.Binary('Pricelist File')
    line_ids = fields.One2many('elneo.supplier.price.update.line','import_id',string='Lines')
    lines_to_update = fields.One2many('elneo.supplier.price.update.line','import_id',string='Lines to Update',domain=[('state','in',('to_update','updating_error','updated_pp','updated'))])
    lines_to_create = fields.One2many('elneo.supplier.price.update.line','import_id',string='Lines to Create',domain=[('state','in',('to_create','error_create','created','create_cancel'))])
    lines_sold = fields.One2many('elneo.supplier.price.update.line','import_id',string='Lines Sold',domain=[('state','in',('to_update','updating_error','updated_pp','updated')),('year_sold_quantity','!=',0)])
    line_ids_display = fields.One2many('elneo.supplier.price.update.line','import_id',string='Lines', limit=999)
    lines_to_update_display = fields.One2many('elneo.supplier.price.update.line','import_id',string='Lines to Update',domain=[('state','in',('to_update','updating_error','updated_pp','updated'))], limit=999)
    lines_to_create_display = fields.One2many('elneo.supplier.price.update.line','import_id',string='Lines to Create',domain=[('state','in',('to_create','error_create','created','create_cancel'))], limit=999)
    lines_sold_display = fields.One2many('elneo.supplier.price.update.line','import_id',string='Lines Sold',domain=[('state','in',('to_update','updating_error','updated_pp','updated')),('year_sold_quantity','!=',0)], limit=999)
    messages = fields.One2many('elneo.supplier.price.update.message','import_id',string='Import Messages')
    increase_price = fields.Float(string='Increase Percent',_compute='_get_increase_percent',help='This is the increase percent from product sold quantities',store=True)
    
    begin_compute = fields.Datetime('Beginning of compute')
    begin_update_purchase_price = fields.Datetime('Beginning of update purchase prices')
    begin_update_sale_price = fields.Datetime('Beginning of update sale price')
    begin_create = fields.Datetime('Beginning of create operation')
    date_done = fields.Datetime('Date done')
    
    progress = fields.Float('Progress', compute='_get_progress')
    time_remaining = fields.Float('Time remaining', compute='_get_time_remaining')
    
    
    
    _rec_name = 'code'
    
    _order='date desc'
    
    @api.one
    def _get_time_remaining(self):
        if self.state == 'computing':
            time_perform = datetime.now() - fields.Datetime.from_string(self.begin_compute)
        elif self.state == 'updating_pps':
            time_perform = datetime.now() - fields.Datetime.from_string(self.begin_update_purchase_price)
        elif self.state == 'updating':
            time_perform = datetime.now() - fields.Datetime.from_string(self.begin_update_sale_price)
        else:
            return
        
        if self.progress and time_perform:  
            self.time_remaining = timedelta(seconds=time_perform.seconds / self.progress).seconds/60.
        
        
    @api.one
    def _get_progress(self):
        nb = 0
        total = self.env['elneo.supplier.price.update.line'].search([('import_id','=',self.id)], count=True)
        if self.state == 'computing':
            nb = self.env['elneo.supplier.price.update.line'].search([('import_id','=',self.id),('state','=','to_update')], count=True)
        if self.state == 'updating_pps':
            nb = self.env['elneo.supplier.price.update.line'].search([('import_id','=',self.id),('state','=','updated_pp')], count=True)
        if self.state == 'updating':
            nb = self.env['elneo.supplier.price.update.line'].search([('import_id','=',self.id),('state','=','updated')], count=True)
        if total:
            self.progress = float(nb)/float(total)
        
    
    @api.one
    def action_draft(self):
        self.state = 'draft'
        lines = self.env["elneo.supplier.price.update.line"].search([('import_id','in',[r.id for r in self])])
        lines.action_draft()
        return True
    
    @api.one
    def action_compute_draft(self):
        self.state = 'draft'
        return True
    
    @api.one
    def action_computing(self):
        self.state = 'computing'
        self.begin_compute = datetime.now()
        self.compute_lines()
        return True
    
    @api.one
    def action_computing_error(self):
        self.state = 'computing_error'
        return True
    
    @api.one
    def action_computed(self):
        self.state = 'computed'
        return True
    
    
    @api.one
    def action_updating_purchase_prices(self):
        self.state = 'updating_pps'
        self.begin_update_purchase_price = datetime.now()
        self.update_price_lines()
        return True
    
    @api.one
    def action_updated_purchase_prices(self):
        self.state = 'updated_pps'
        return True
    
    @api.one
    def action_updating(self):
        self.state = 'updating'
        self.begin_update_sale_price = datetime.now()
        self.update_sale_price_lines()
        return True
    
    @api.one
    def action_updating_error(self):
        self.state = 'updating_error'
        return True
    
    @api.one
    def action_cancel(self):
        self.state = 'cancel'
        return True
    
    @api.one
    def action_done(self):
        res = False
        if self._update_supplierinfo():
            res=True
        if self._check_done():
            self.state = 'done'
            self.date_done = datetime.now()
            res = True
        return res
    
    # Check lines status to make the Import done or not
    def _check_done(self,cr,uid,ids,context=None):
        res = True
        for update in self.browse(cr,uid,ids,context=context):
            for line in update.lines_to_update:
                if line.state not in ('updated') :
                    return False
                
        return res
    
    def _update_supplierinfo(self,cr,uid,ids,context=None):
        res = True
        suppinfo_obj = self.pool.get('product.supplierinfo')
        for update in self.browse(cr,uid,ids,context=context):
            for line in update.line_ids:
                if line.state == 'updated':
                    for suppinfo in line.suppinfo_ids:
                        suppinfo_obj.write(cr,uid,suppinfo.id,{'last_price_update_date':datetime.now(),'last_supplier_price_update':update.id},context=context)
        
        return res
    
    # Funcion to import supplier pricelist in CSV
    # Two kind of file structure : Landefeld or Standard
    # Standard : Columns must match the object column names but only required columns (required=True in the object) are mandatory
    @api.one
    def _import_csv(self):
        update = None
        try:
            att_obj = self.env['ir.attachment']
            for update in self:
                
                #if not update.pricelist_file :
                    #self._message(cr, uid, [update.id], _('Impossible to import. The Csv file is not defined!'), context)
                
                att_ids = att_obj.search([('res_model', '=', 'elneo.supplier.price.update'), ('res_id', '=', update.id)])
                
                if att_ids:
                    pricelist_file = att_ids[0]
                else:
                    return self._import_csv_big()
                
                if not pricelist_file:
                    self._message(_('Impossible to import. The Csv file is not defined!'))
                csvfile = base64.decodestring(pricelist_file.datas)
                rows = csvfile.split("\r\n")
                total = len(rows)
                
                columns = self._get_columns(row=rows[0])
                
                valid = False
                if update.type == 'elneo_standard':
                    valid = self._validate_columns(columns)
                elif update.type == 'landefeld':
                    if (len(columns) == 25):
                        valid = True
                
                # Remove header line        
                rows.pop(0)
                
                if (valid):
                    lines_pool = self.env['elneo.supplier.price.update.line']
                    lines_to_delete = lines_pool.search([('import_id','=',update.id)])
                    if lines_to_delete:
                        lines_to_delete.unlink()
                    for row in rows:
                        if update.type == 'elneo_standard':
                            value = self._get_elneo_standard(row,columns)
                        elif update.type == 'landefeld':
                            value = self._get_landefeld(row)
                            
                        if value :
                            value['import_id']=update.id
                            result = self.env['elneo.supplier.price.update.line'].create(value)
                else:
                    self._message(_('ERROR : The csv file is not in the expected format'))
                
        except Exception,e:
            # We raise Exception but we stay in 'Draft' state - just log the message
            self._message(_('ERROR : ') + unicode(e.message))
            raise Warning('Import Error','Unknown error during import!' + unicode(e))

        return True
    
    #for big pricelists, use sql copy method from file already in filesystem  
    @api.one
    def _import_csv_big(self):
        
        self._cr.execute("drop table if exists pricelist_landefeld_full");
        
        self._cr.execute("""
        CREATE TABLE pricelist_landefeld_full
    (
      "Artikelnummer" Character varying(255),
      "KundenArtNr" Character varying(255),
      "Generalrabattfaehig" Character varying(255),
      "Artikelgruppe" Character varying(255),
      "Bezeichnung1" Character varying(255),
      "Bezeichnung2" Character varying(255),
      "VPE" Character varying(255),
      "Einheit" Character varying(255),
      "Preisfaktor" Character varying(255),
      "AbMenge" Character varying(255),
      "Marktpreis" Character varying(255),
      "Preis" Character varying(255),
      "Rabatt" Character varying(255),
      "Nettopreis" Character varying(255),
      "Eclass" Character varying(255),
      "Zollwarennr" Character varying(255),
      "Katalogseite" Character varying(255),
      col1 Character varying(255),
      col2 Character varying(255),
      "Gewicht in kg" Character varying(255),
      col3 Character varying(255),
      "Alte Artikelnummer" Character varying(255),
      "EindeutigeNr" Character varying(255),
      "Produktgruppe" Character varying(255),
      col4 Character varying(255)
    )
    WITH (
      OIDS=FALSE
    );""")
        
        ids = [r.id for r in self]
        
        self._cr.execute("set client_encoding to 'latin1';")
        self._cr.execute('truncate table pricelist_landefeld_full;')
        self._cr.execute("copy pricelist_landefeld_full from '/home/elneo/landefeld_pricelist/pricelist.csv' with header delimiter ';' quote '\"' CSV;")
        self._cr.execute("set client_encoding to 'UTF8';")
        self._cr.execute("DELETE FROM elneo_supplier_price_update_line WHERE import_id = "+str(ids[0]))
        self._cr.execute("""INSERT INTO elneo_supplier_price_update_line(
            create_uid, create_date, write_date, write_uid, import_id, 
            product_code, name_tmpl, quantity, public_price, brut_price, net_price, multiply, 
            discount, product_group, weight,state)
select 1, now(), now(), 1, """+str(ids[0])+""", 
"Artikelnummer", "Bezeichnung1", 
to_number(replace(NULLIF("AbMenge",' '),',','.'),'999999999.99'), 
case when to_number(replace(NULLIF("Preisfaktor",' '),',','.'),'999999999.99') != 1.0 then to_number(replace(NULLIF("Marktpreis",' '),',','.'),'999999999.99')/to_number(replace(NULLIF("Preisfaktor",' '),',','.'),'999999999.99') else to_number(replace(NULLIF("Marktpreis",' '),',','.'),'999999999.99')::float end, 
case when to_number(replace(NULLIF("Preisfaktor",' '),',','.'),'999999999.99') != 1.0 then to_number(replace(NULLIF("Preis",' '),',','.'),'999999999.99')/to_number(replace(NULLIF("Preisfaktor",' '),',','.'),'999999999.99') else to_number(replace(NULLIF("Preis",' '),',','.'),'999999999.99') end, 
case when to_number(replace(NULLIF("Preisfaktor",' '),',','.'),'999999999.99') != 1.0 then to_number(replace(NULLIF("Nettopreis",' '),',','.'),'999999999.99')/to_number(replace(NULLIF("Preisfaktor",' '),',','.'),'999999999.99') else to_number(replace(NULLIF("Nettopreis",' '),',','.'),'999999999.99') end, 
to_number(replace(NULLIF("Preisfaktor",' '),',','.'),'999999999.99'),
to_number(replace(NULLIF("Rabatt",' '),',','.'),'999999999.99'),
"Produktgruppe",
to_number(NULLIF(replace(replace("Gewicht in kg",',','.'),' ',''),''),'999999999.99'),
'draft'
from pricelist_landefeld_full;""")
        return True
        
    
    @api.one
    def _get_landefeld(self,row):
        res = {}
        
        col = self._get_columns(row)
        
        try:
            if (len(col) == 25):
                res['product_code']=col[0].lstrip('"').rstrip('"')
                res['name_tmpl']=col[4].lstrip('"').rstrip('"')
                res['quantity']=col[9].replace('"','').replace(",",".")
                
                if(res['quantity']!="0"):
                    res['public_price'] = (float(col[10].replace('"','').replace(",",".")) / float(res['quantity']))
                    res['brut_price']=(float(col[11].replace('"','').replace(",",".")) / float(res['quantity']))
                    res['net_price']=(float(col[13].replace('"','').replace(",",".")) / float(res['quantity']))
                else:
                    res['public_price'] = float(col[10].replace('"','').replace(",","."))
                    res['brut_price']=float(col[11].replace('"','').replace(",","."))
                    res['net_price']=float(col[13].replace('"','').replace(",","."))
                    res['quantity']=1.0
                    
                    
                res['multiply']=col[8].replace('"','').replace(",",".")
                res['discount']=col[12].replace('"','').replace(",",".")
                res['product_group']=col[23].lstrip('"').rstrip('"')
                try:
                    res['weight']=float(col[19].replace('"','').replace(",","."))
                except:
                    res['weight']=0.0
            else:
                res=None
        
        except Exception,e:
            self._message(_('ERROR : During getting data from Landefeld Line :' + unicode(e)))
            res=None
            pass
            
        return res
        
    # If the file type is 'elneo_standard'
    @api.multi 
    def _get_elneo_standard(self,row,header): 
        res = {}
        
        col = self._get_columns(row)
        line_obj = self.pool.get('elneo.supplier.price.update.line')
        
        if col and (len(col) == len (header)):
            i=0
            for head in header :
                if (line_obj._columns[head]._type) in ['Float','float']:
                    res[head]=col[i].replace(",",".")
                else:
                    res[head]=col[i]
                i=i+1
        
        return res   
        
    # Simple split to get an array of columns
    def _get_columns(self,row):
        res=[]
        
        if row:
            columns = [x.strip() for x in row.split(";")]
            res = columns
        
        
        return res
    
    # Function to get required columns and to reject file that does not contain these columns
    @api.one
    def _validate_columns(self,columns):
        res = True
        line_obj = self.pool.get('elneo.supplier.price.update.line')
        # We parse the update line object and we must find the required columns in the imported file
        for (column,value) in line_obj._columns.iteritems():
            if (value.required and column not in columns):
                self._message(_('Impossible to import. Required fields are not present in the file!'))
                res = False
                
        return res
    
    
    # Function that launch the thread to import
    @api.one
    def import_lines(self):
        '''
        thread_import = threading.Thread(target=self._import_csv,args=(cr, uid, ids, context))
        thread_import.start()
        '''
        self._import_csv()
        return True

    
    # Get Product old properties to fill the columns
    def _get_product_pricelist_properties(self,cr,uid,id,context=None):
        res={}
        
        partnerinfo = self.pool.get('pricelist.partnerinfo').browse(cr,uid,id,context=context)
        if partnerinfo:
            res['old_brut_price']=partnerinfo.brut_price
            res['old_net_price']=partnerinfo.price
            res['old_discount']=partnerinfo.discount
            res['old_public_price']=partnerinfo.public_price
        
        return res
    
    # Get product sold quantity - If multiple products (due to the same supplier code)
    def _get_product_sold_quantity(self,cr,uid,ids,context=None):
        res = 0.0
        
        new_date = datetime.now()-timedelta(days=365)
        new_date = new_date.strftime('%Y-%m-%d')
        quantity = 0
        for id in ids:
            self._cr.execute("SELECT ail.quantity FROM account_invoice_line ail JOIN account_invoice ai ON ail.invoice_id = ai.id WHERE ail.product_id = " + str(id) + " AND ai.date_invoice >= '" + str(new_date) + "' AND ai.type = 'out_invoice'")
            for tmp in map(lambda x: x[0], cr.fetchall()):
                quantity = quantity + tmp
        #line_ids = self.pool.get('account.invoice.line').search(cr,uid,[('product_id','in',ids),('invoice_id.date_invoice','>=',new_date),('invoice_id.type','=','out_invoice')])
        
        #for line in self.pool.get('account.invoice.line').browse(cr,uid,line_ids,context=context):
            #res=res+line.quantity
        res = quantity
        return res
    
    # Search Method to find products based on supplier product code or on product default code if supplier is the same
    # SQL version to optimize performances
    @api.one
    def _get_supplierinfo(self):
        self._cr.execute("SELECT id FROM product_supplierinfo WHERE product_code = '" + str(self.product_code) + "' AND name = " + str(self.import_id.supplier_id.id))
        
        res = map(lambda x: x[0], self._cr.fetchall())
        
        if len(res) == 0 :
            self._cr.execute("SELECT ps.id FROM product_supplierinfo ps JOIN product_template pt ON ps.product_id = pt.id JOIN product_product pp ON pp.product_tmpl_id = pt.id WHERE pp.default_code = '" + self.product_code + "'")
            res = map(lambda x: x[0], self._cr.fetchall())
        
        return res
    
    @api.multi
    def _get_product_ids(self):
        res = []
        
        for supplierinfo in self:     
            self._cr.execute("SELECT pp.id FROM product_product pp WHERE pp.product_tmpl_id = " + str(supplierinfo.product_id.id))       
            for id in map(lambda x: x[0], self._cr.fetchall()):
                res.append(id)

        return res
    
    
    def _update_lines(self,properties):
        res = True
        
        tmp=""
        i=0
        sep = ""
        for property in properties:
            if not (isinstance(properties[property],list)):
                if i!=0:
                    sep = ","
                tmp=tmp + sep + str(property) + " = '" + str(properties[property]) +"'"
                i+=1
        
        for id in self :
            sql = "UPDATE elneo_supplier_price_update_line SET " + tmp + " WHERE id="+str(id)
            self._cr.execute(sql)  
                
        
        
        return res
    
    def _link_products(self,line,product_ids):
        res = True
        
        sql = "DELETE FROM elneo_supplier_price_update_line_product_rel WHERE update_line_id = " + str(line.id)
        
        self._cr.execute(sql)
        unique_ids=[]
        [unique_ids.append(item) for item in product_ids if item not in unique_ids]
        for product_id in unique_ids:
            sql = "INSERT INTO elneo_supplier_price_update_line_product_rel(update_line_id,product_id) VALUES (" + str(line.id) + "," + str(product_id) + ")"
            self._cr.execute(sql)
        
        return res
        
        
    # Function that :
    # - Makes the link between supplier codes and products
    # - If product exists, change the line state to 'To Update'
    # - If not, change the line state to 'To Create'
    @api.multi
    def _compute(self):
        
        def compute_part(line_ids):
            
            line_ids._set_suppinfos()
                
            line_ids._set_products()
            
            line_ids.update_lines()
            
            self.env.cr.commit()

            
            line_obj = self.env['elneo.supplier.price.update.line']
            lines_to_create = line_obj.search([('id','in',[line.id for line in line_ids]),('suppinfo_ids','=',False)])
            lines_to_update = line_obj.search([('id','in',[line.id for line in line_ids]),('suppinfo_ids','!=',False)])
            
            lines_to_update.action_to_update()
            lines_to_create.action_to_create()
            
            self.env.cr.commit()        
            
            return True
        
        res = True
        cr2 = sql_db.db_connect(self.env.cr.dbname).cursor()
        uid, context = self.env.uid, self.env.context
        with api.Environment.manage():
            self.env = api.Environment(cr2, uid, context)
            update = None
            try:
                for update in self:
                    update.begin_compute = datetime.now()
                    
                    all_line_ids = self.env["elneo.supplier.price.update.line"].search([('import_id','=',update.id),('state','=','draft')])
                    all_line_ids_len = len(all_line_ids)
                    i = 0
                    while i < all_line_ids_len:
                        current_line_ids = all_line_ids[i:i+100]
                        compute_part(current_line_ids)
                        if all_line_ids_len:
                            update.percent_operation_compute = i*100./all_line_ids_len
                        i = i+100
    
                    self.action_computed()
                
            except Exception,e:
                self._message(_('ERROR : During Import lines - ') + unicode(e.message))
                self.action_computing_error()
                raise Warning('ERROR',_('ERROR : During Import lines - ') + unicode(e.message))
            finally:
                try:                
                    self.env.cr.commit()
                except Exception:
                    pass
                try:                
                    self.env.cr.close()
                except Exception:
                    pass
            
        return res
    
    # Main function to launch the compute thread
    @api.multi
    def compute_lines(self):
        res=True
        
        if self._context and self._context.get('no_thread',False):
            return self._compute()
        else:
            thread_compute = threading.Thread(target=self._compute,args=())
            thread_compute.start()
        
        return res
        
    # The thread that update the pruchase prices (INSERT)
    @api.one
    def _update_purchase_prices(self):
        res=True
        
        cr = sql_db.db_connect(self.env.cr.dbname).cursor()
        uid, context = self.env.uid, self.env.context
        with api.Environment.manage():
            self.env = api.Environment(cr, uid, context)
            try:
                self.begin_update = datetime.now()
                i=0
                complete = len(self.lines_to_update)
                percent = 0.0
                
                jump = 100
                lines = self.lines_to_update[i:jump]
                
                while lines:
                    #update pricelist_partnerinfo
                    self._cr.execute("""
                        update pricelist_partnerinfo set price = req.net_price, brut_price = req.brut_price, discount = req.discount, public_price = req.public_price
                        from
                        (
                        SELECT quantity, net_price,sr.suppinfo_id, brut_price, discount, public_price, CURRENT_TIMESTAMP 
                        FROM elneo_supplier_price_update_line ul 
                        LEFT JOIN elneo_supplier_price_update_line_suppinfo_rel sr 
                        ON ul.id=sr.update_line_id 
                        WHERE ul.id in %s AND state='to_update'                        
                        ) req
                        where req.suppinfo_id = pricelist_partnerinfo.suppinfo_id and pricelist_partnerinfo.min_quantity = req.quantity""",(tuple([line.id for line in lines]),))
                    
                    #insert history line
                    self._cr.execute("""
                        INSERT INTO pricelist_partnerinfo_history (min_quantity, price, suppinfo_id, brut_price, discount, update_method, date) 
                        SELECT quantity, net_price,sr.suppinfo_id, brut_price, discount, 'price_list_file', CURRENT_TIMESTAMP 
                        FROM elneo_supplier_price_update_line ul JOIN elneo_supplier_price_update_line_suppinfo_rel sr ON ul.id=sr.update_line_id 
                        WHERE ul.id in %s AND state='to_update'""",(tuple([line.id for line in lines]),))
                    lines.action_updated_purchase_price()
                    i=i+jump
                    percent = (i / complete) * 100.
                    cr.commit()
                    lines = self.lines_to_update[i:i+jump]
                    
                self.action_updated_purchase_prices()
                
            except Exception,e:
                self._message(_('ERROR : During Purchase Price Update lines - ') + unicode(e))
                self.action_updating_error()
            finally:
                try:                
                    cr.commit()
                except Exception:
                    pass
                try:                
                    cr.close()
                except Exception:
                    pass
        
        return res
  
    # Main function that launches the update purchase price thread 
    def update_price_lines(self):
        res=True
        
        if self._context and self._context.get('no_thread',False):
            return self._update_purchase_prices()
        else:
            thread_compute = threading.Thread(target=self._update_purchase_prices,args=())
            thread_compute.start()
        
        return res
    
    @api.one
    def _update_sale_prices(self):
        cr = sql_db.db_connect(self.env.cr.dbname).cursor()
        uid, context = self.env.uid, self.env.context
        with api.Environment.manage():
            self.env = api.Environment(cr, uid, context)
            try:
                i=0
                complete = len(self.lines_to_update)
                percent = 0.0
                
                jump = 100
                lines = self.lines_to_update[i:jump]
                
                while lines:
                    #find all product_ids
                    self._cr.execute("select product_id from elneo_supplier_price_update_line_product_rel rel left join elneo_supplier_price_update_line line on rel.update_line_id = line.id where line.id in %s and line.state = 'updated_pp'",(tuple([line.id for line in lines]),))
                    product_ids = [product_id for (product_id,) in cr.fetchall()]
                    #for each product, write it to compute sale price, and update line state
                    for product in self.env['product.product'].browse(product_ids):
                        product.product_tmpl_id._get_list_price()
                    lines.action_updated()
                    i=i+jump
                    percent = (i / float(complete)) * 100.
                    cr.commit()
                    lines = self.lines_to_update[i:i+jump]
                
                #finally update import state
                self.action_done()
                cr.commit()
                    
            except Exception,e:
                self._message(_('ERROR : During Purchase Price Update lines - ') + unicode(e))
                self.action_updating_error()
            finally:
                try:                
                    cr.commit()
                except Exception:
                    pass
                try:                
                    cr.close()
                except Exception:
                    pass
        
    
    def update_sale_price_lines(self):
        res=True
        
        if self._context and self._context.get('no_thread',False):
            return self._update_sale_prices()
        else:
            thread_compute = threading.Thread(target=self._update_sale_prices,args=())
            thread_compute.start()
        
        return res
    
    def _link_suppinfos(self,line,pricelists):
        res = False
        
        suppinfo_ids = []
        for pricelist in pricelists:
            suppinfo_ids.append(pricelist.suppinfo_id.id)
        
        line.write({'suppinfo_ids':[(6,0,suppinfo_ids)]})
        
        
        return res
    
    # Take all the lines in 'to_create' state and create the corresponding products
    @api.multi
    def _create_lines(self):
        res = True
        
        cr = pooler.get_db(self._cr.dbname).cursor()
        try:
            for update in self:
                # Initialize the operation percent
                update.write({'percent_operation_create':0.0})
                i=0.0
                complete = len(update.lines_to_create)
                for line in update.lines_to_create:
                    try:
                        # We take only lines to create
                        if line.state =='to_create':
                            values = update._get_values_to_insert()
                            
                            product_created = self.env['product.product'].create(values)
                            if product_created:
                                template = product_created.product_tmpl_id.id
                                if template:
                                    template._update_translations(line)
                                # Make the link with the product to keep history
                                self._link_products(line, [product_created.id])
                                # Creates the pricelist line for the created product for the quantity
                                pricelist = self._create_pricelist(line)
                                if not pricelist:
                                    raise Exception('Error when creating pricelist for the product : ' + str(product_created.id))
                                else:
                                    self._link_suppinfos(line, [pricelist])
                                line.action_created() 
                                cr.commit()
                        
                    except Exception,e:
                        self._message(_('ERROR : During Create lines - ') + unicode(e))
                        line.action_error_create()

                    i= i + 1.0
                    percent = (i / complete) * 100
                    update.write({'percent_operation_create':percent})
                    cr.commit()
                    
                        
        except Exception,e:
            _logger.warning('Purchase prices create error')
        finally:
            try:                
                cr.commit()
                _logger.warning('Purchase prices create')
            except Exception:
                pass
            try:                
                cr.close()
            except Exception:
                pass

        return res
    
    # For each language, update or create translations
    def _update_translations(self,line):
        res=True
        line_obj = self.pool.get('elneo.supplier.price.update.line')
        if line.name_tmpl:
            if line.name_fr:
                line_obj._update_product_translations(line.name_tmpl,line.name_fr, self.id,'fr_BE')
            if line.name_nl:
                line_obj._update_product_translations(line.name_tmpl,line.name_nl, self.id,'nl_BE')
            if line.name_de:
                line_obj._update_product_translations(line.name_tmpl,line.name_de, self.id,'de')
            if line.name_en:
                line_obj._update_product_translations(line.name_tmpl,line.name_en, self.id,'en_US')
        
        
        return res
    
    # Create the product pricelist information
    def _create_pricelist(self,line):
        res = None
        for product in line.product_ids:
            value = {}
            
            # Set every supplierinfo values
            value['product_id']=product.product_tmpl_id.id
            value['name']=line.import_id.supplier_id.id
            if line.min_quantity:
                value['min_qty']=line.min_quantity
            else:
                value['min_qty']=1
                
            if line.name_tmpl:
                value['product_name']=line.name_tmpl
            if line.product_code:
                value['product_code']=line.product_code
            
            value['pack']=line.pack
            
            suppinfo_id = self.env['product.supplierinfo'].create(value)
            
            #Set every pricelist values
            if suppinfo_id:
                value = {}
                value['suppinfo_id']=suppinfo_id
                value['min_quantity']=line.quantity
                value['brut_price']=line.brut_price
                value['discount']=line.discount
                value['public_price']=line.public_price
                value['price']=line.net_price
                value['update_methode']='price_list_file'
                value['date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                

                pricelist_id = self.env['pricelist.partnerinfo'].create(value)
                res = pricelist_id
                if not pricelist_id:
                    res = False
            else:
                res = False    
                
            break
        
        
        return res
    
    # Launch product lines creation thread
    def create_lines(self,cr,uid,ids,context=None):
        res= True
        
        thread_compute = threading.Thread(target=self._create_lines,args=(cr, uid, ids, context))
        thread_compute.start()
        
        return res
    
    # Construct the data for the new created product
    @api.one
    def _get_values_to_insert(self):
        res={}
        
        if self.product_code:
            res['default_code']=self.product_code
            res['list_price']=self.public_price
            res['public_price']=self.public_price
        if self.product_category_id:
            res['categ_id']=self.product_category_id.id
        if self.name_tmpl:
            res['name']=self.name_tmpl
        if self.weight:
            res['weight_net']=self.weight
 
        return res
   
    @api.one
    def _message(self,message):
        self.env['elneo.supplier.price.update.message'].create({'import_id':self.id,'message':message,'date':datetime.now()})
    
    def create(self, cr, uid, vals, context=None):
        sequence=self.pool.get('ir.sequence').get(cr, uid, 'elneo.supplier.price.update')
        vals['code']=sequence
        return super(elneo_supplier_price_update, self).create(cr, uid, vals, context=context)
        
elneo_supplier_price_update()

class CsvImportError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


class elneo_supplier_price_update_line(models.Model):
    _name='elneo.supplier.price.update.line'
    
    
    def _set_products(self):
        #insert values in many2many between products and update_line
        #WARNING : this function must be called after _set_suppinfos
        
        res = True
        
        line_ids = [r.id for r in self]
        
        sql =  "delete from elneo_supplier_price_update_line_product_rel where update_line_id in %s"
        
        self._cr.execute(sql,(tuple(line_ids),))
        
        self._cr.commit()
        
        sql = """
            insert into elneo_supplier_price_update_line_product_rel 
        select distinct line.id, p.id from elneo_supplier_price_update_line_suppinfo_rel rel
        left join elneo_supplier_price_update_line line on line.id = rel.update_line_id
        left join product_supplierinfo ps 
        left join product_product p on p.product_tmpl_id = ps.product_tmpl_id
        on ps.id = rel.suppinfo_id
        where line.id in %s"""
        
        self._cr.execute(sql,(tuple(line_ids),))

        return res
    
    @api.multi
    def _set_suppinfos(self):
        res = True
        
        sql =  "delete from elneo_supplier_price_update_line_suppinfo_rel where update_line_id in %s"
        line_ids = [r.id for r in self]
        self._cr.execute(sql,(tuple(line_ids),))
        
        self._cr.commit()
        
        sql = """
        insert into elneo_supplier_price_update_line_suppinfo_rel 
            select line_id,suppinfo_id from
                (select distinct line.id line_id,
                case when suppinfo.id is not null then suppinfo.id else suppinfo_meth2.id end suppinfo_id
                from elneo_supplier_price_update_line line
                    left join elneo_supplier_price_update import on import.id = line.import_id
                    left join product_product product_meth2 on (UPPER(product_meth2.default_code) = UPPER(line.product_code))
                    left join product_supplierinfo suppinfo_meth2 on ((suppinfo_meth2.product_code is null or suppinfo_meth2.product_code = '') and suppinfo_meth2.product_tmpl_id = product_meth2.product_tmpl_id and suppinfo_meth2.name = import.supplier_id and product_meth2.active)
                    left join product_supplierinfo suppinfo 
                left join product_template suppinfo_product_tmpl 
                    left join product_product suppinfo_product on (suppinfo_product_tmpl.id = suppinfo_product.product_tmpl_id)
                on suppinfo.product_tmpl_id = suppinfo_product_tmpl.id
                    on (UPPER(suppinfo.product_code) = UPPER(line.product_code) and suppinfo.name = import.supplier_id)
                where line.id in %s and (suppinfo_product.active or suppinfo_product.active is null) and (product_meth2.active or product_meth2 is null)
                order by line.id) suppinfo_not_null WHERE suppinfo_id IS NOT NULL
        """
        
        self._cr.execute(sql,(tuple(line_ids),))

        return res
    
    def update_lines(self):
        res=True
        line_ids = [r.id for r in self]
        
        sql = """
        
        update elneo_supplier_price_update_line 

            set old_brut_price = req3.brut_price, old_discount = req3.discount, old_net_price = req3.price, 
            old_public_price = req3.public_price, year_sold_quantity = req3.invoiced_quantity, 
            suppinfo_id = req3.suppinfo_id, 
            net_price_difference = req3.net_price_difference, 
            increase_price = req3.increase_price, product_category_id = req3.category_id, state = 'to_update'
                from
                (
                select req2.brut_price, req2.discount, req2.price, req2.public_price, sum(req2.invoiced_quantity) as invoiced_quantity, req2.suppinfo_id as suppinfo_id, 
                req2.net_price-req2.price as net_price_difference, (req2.net_price-req2.price)*sum(req2.invoiced_quantity) as increase_price, req2.id, req2.net_price, req2.category_id from 
                    (
                    select req.id, req.product_code, pl2.price, pl2.discount, pl2.public_price, pl2.brut_price, pl2.suppinfo_id, req.product_id,
                    
                    case 
                        when inv.date_invoice >= (now() - interval '1 year') 
                        then
                            case
                            when inv.type = 'out_invoice' 
                                then inv_line.quantity 
                                when inv.type = 'out_refund' 
                                then -inv_line.quantity 
                            end 
                        else 0 
                        end 
                    as invoiced_quantity, req.net_price, req.category_id
                    
                    from 
                    (
                    select line.net_price, line.id, line.quantity, line.product_code,
                    rel_suppinfo.suppinfo_id, p.id AS product_id, case when line.product_category_id is null then product_group.category_id else line.product_category_id end as category_id
                    from elneo_supplier_price_update_line line
                    left join product_group on product_group.name = line.product_group
                    left join elneo_supplier_price_update import on import.id = line.import_id
                    left join elneo_supplier_price_update_line_suppinfo_rel rel_suppinfo 
                    left join product_supplierinfo ps 
                        left join product_product p on p.product_tmpl_id = ps.product_tmpl_id
                    on ps.id = rel_suppinfo.suppinfo_id
                    on rel_suppinfo.update_line_id = line.id                    
                    where line.id in %s
                    order by line.id
                    ) req
                    left join pricelist_partnerinfo pl1 on (pl1.suppinfo_id = req.suppinfo_id and pl1.min_quantity = req.quantity)
                    left join pricelist_partnerinfo pl2 on (pl2.suppinfo_id = req.suppinfo_id and pl2.min_quantity = req.quantity)
                    
                    left join account_invoice_line inv_line 
                        left join account_invoice inv on (inv.id = inv_line.invoice_id)
                    on (inv_line.product_id = req.product_id)
                    
                    group by req.id, pl2.id, req.product_id,inv.id,inv_line.id, req.product_code, req.net_price, req.category_id
                    having pl2.id = max(pl1.id)
                    ) req2
                    group by req2.id, req2.price, req2.discount, req2.public_price, req2.brut_price, req2.suppinfo_id, req2.product_id, req2.product_code, req2.net_price, req2.category_id
                    order by req2.product_code
                ) req3
                where req3.id = elneo_supplier_price_update_line.id
        """
        
        self._cr.execute(sql,(tuple(line_ids),))
        
        return res
    
    #Update products translations
    def _update_product_translations(self, name_tpl, translation, product_template_id,lang, context=None):
        if not context:
            context = {}
        
        ir_translations = self.env['ir.translation'].search([('lang','=',lang),('name','=','product.template,name'),('res_id','=',product_template_id)])
        
        if ir_translations:
            ir_translations.src = name_tpl
            ir_translations.value = translation
        else:
            self.env['ir.translation'].create({
                 'name':'product.template,name',
                 'lang':lang,
                 'src':name_tpl,
                 'res_id':product_template_id,
                 'type':'model',
                 'value':translation,
            })
        return True
    
    def _get_products(self, cr, uid, ids, name, args, context=None):
        res={}
        
        for line in self.browse(cr,uid,ids,context=context):
            suppinfo_ids = self.pool.get('product.supplierinfo').search(cr,uid,[('product_code','=',line.product_code)],context=context)
            res[line.id]=[]
            for suppinfo in self.pool.get('product.supplierinfo').browse(cr,uid,suppinfo_ids,context=context):
                prod_ids = self.pool.get('product.product').search(cr,uid,[('product_tmpl_id','=',suppinfo.product_id.id)])
                if (prod_ids):
                    for prod_id in prod_ids:
                        if prod_id not in res[line.id]:
                            res[line.id].append(prod_id)
                    
        
        return res
    
    # Calculate the unit net price difference between the old pricelist and the new one
    @api.depends('price','net_price')
    def _get_net_price_difference(self,cr,uid,ids,name,args,context=None):
        res={}
        for line in self.pool.get('elneo.supplier.price.update.line').browse(cr,uid,ids,context=context):
            if (len(line.product_ids) > 0):
                
                suppinfo_ids = self.pool.get('product.supplierinfo').search(cr,uid,[('product_id','=', line.product_ids[0].product_tmpl_id.id),('name','=',line.import_id.supplier_id.id)],context=context)
                for suppinfo in self.pool.get('product.supplierinfo').browse(cr,uid,suppinfo_ids,context=context):
                    the_pricelist = None
                    ordered_list = sorted(suppinfo.displayed_pricelist_ids,key=lambda x : x.min_quantity, reverse=False)
                    for pricelist in ordered_list:
                        if line.quantity <= pricelist.min_quantity:
                            the_pricelist = pricelist
                            break
                        
                    if the_pricelist:
                        if(line.quantity and line.quantity !=0):
                            quantity = line.quantity
                        else:
                            quantity = 1
                        if the_pricelist.price <= line.net_price :
                            res[line.id] = (1- (the_pricelist.price / (line.net_price))) * 100
                        else:
                            res[line.id] = - (1 - ((line.net_price) / the_pricelist.price)) * 100

        return res
    
    @api.depends('old_net_price','net_price')
    def _get_increase_price(self,cr,uid,ids,name,args,context=None):
        res={}
        
        for line in self.pool.get('elneo.supplier.price.update.line').browse(cr,uid,ids,context=context):
            res[line.id] = (line.net_price - line.old_net_price) * line.year_sold_quantity
        
        return res
    
    
    
    
    import_id = fields.Many2one('elneo.supplier.price.update')
    product_code = fields.Char(string='Product Supplier Code',size=64)
    quantity = fields.Float(string='Quantity')
    brut_price = fields.Float(string='Brut Price')
    discount = fields.Float(string='Discount')
    net_price = fields.Float(string='Net Price')
    multiply = fields.Float(string='Multiply')
    public_price = fields.Float(string='Public Price')
    product_group = fields.Char(string="Product Group",size=255)
    min_quantity = fields.Float(string='Min. Buy Quantity')
    pack = fields.Boolean('Pack')
    weight = fields.Float('Weight')
    product_ids = fields.Many2many('product.product','elneo_supplier_price_update_line_product_rel','update_line_id','product_id','Products')
    state = fields.Selection([('draft','Draft'),('to_update','To Update'),('to_create','To Create'),('error_create','Create Error'),('update_error','Update Error'),('updated_pp','Purchase Price Updated'),('updated','Updated'),('created','Created'),('create_cancel','Create Cancelled')],string='State',readonly=True, default='draft')
    product_category_id = fields.Many2one('product.category','Product Category')
    old_brut_price = fields.Float(string='Old Brut Price')
    old_net_price = fields.Float(string='Old Net Price')
    old_discount = fields.Float('Old Discount')
    old_public_price = fields.Float('Old Public Price')
    year_sold_quantity = fields.Float(string='Last Year Sold Quantity')
    increase_price = fields.Float(_compute='_get_increase_price',store=True,string='Increase')
    name_tmpl = fields.Char(size=128,string='Name Template')
    name_fr = fields.Char(size=128,string='Name FR')
    name_nl = fields.Char(size=128,string='Name NL')
    name_en = fields.Char(size=128,string='Name EN')
    name_de = fields.Char(size=128,string='Name DE')
    net_price_difference = fields.Float(_compute='_get_net_price_difference',store=True,string='Net Price Difference')
    suppinfo_id = fields.Many2one('product.supplierinfo','Supplier Info')
    suppinfo_ids = fields.Many2many('product.supplierinfo','elneo_supplier_price_update_line_suppinfo_rel','update_line_id','suppinfo_id','Supplier Info')
             
    _rec_name='product_code'
    
    @api.one
    def action_draft(self):
        self.state = 'draft'
        return True
    
    @api.one
    def action_to_update(self):
        self.state = 'to_update'
        return True
    
    @api.one
    def action_to_create(self):
        self.state = 'to_create'
        return True
    
    @api.one
    def action_error_create(self):
        self.state = 'error_create'
        return True
    
    @api.one
    def action_error_update(self):
        self.state = 'error_update'
        return True
    
    @api.one
    def action_updating(self):
        self.state = 'updating'
        return True
    
    @api.one
    def action_created(self):
        self.state = 'created'
        return True
    
    @api.one
    def action_updated_purchase_price(self):
        self.state = 'updated_pp'
        return True
    
    @api.one
    def action_updated(self):
        self.state = 'updated'
        return True
    
    @api.one
    def action_create_cancel(self):
        self.state = 'create_cancel'
        return True

elneo_supplier_price_update_line()


class elneo_supplier_price_update_message(models.Model):
    _name='elneo.supplier.price.update.message'
    
    import_id = fields.Many2one('elneo.supplier.price.update','Import')
    message = fields.Text(string='Message',readonly=True)
    date = fields.Datetime(string='Date',readonly=True)
    
elneo_supplier_price_update_message()


