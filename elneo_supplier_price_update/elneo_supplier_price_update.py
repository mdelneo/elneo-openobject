from datetime import datetime, timedelta
import threading
import base64

import time
import shlex,subprocess
import os
import sys
from openerp import models,fields,api, pooler, netsvc
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
            'percent_operation_update':0,
            'percent_operation_create':0,
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
          
    code = fields.Char('Code',size=30,help='The Import Code',readonly=True)
    supplier_id = fields.Many2one('res.partner',string="Supplier",domain=[('supplier','=','True')],required=True)
    date = fields.Datetime('Date',help='Date of Import')
    type = fields.Selection([('landefeld','Landefeld'),('elneo_standard','Standard')],string="Type",required=True,help='The type of input will determine which kind of file structure can be imported.')
    save_in_sale_price_fixed = fields.Boolean('Save in Sale Price')
    complete_list_price = fields.Boolean('Complete Price List')
    pricelist_file = fields.Binary('Pricelist File')
    line_ids = fields.One2many('elneo.supplier.price.update.line','import_id',string='Lines')
    state = fields.Selection([('draft','Draft'),('computing','Computing'),('computing_error','Computing Error'),('computed','Computed'),('updating_pps','Updating Purchase Prices'),('updated_pps','Purchase Prices Updated'),('updating','Updating'),('updating_error','Updating Error'),('done','Done'),('cancel','Canceled')],string='State',readonly=True)
    lines_to_update = fields.One2many('elneo.supplier.price.update.line','import_id',string='Lines to Update',domain=[('state','in',('to_update','updating_error','updated_pp','updated'))])
    lines_to_create = fields.One2many('elneo.supplier.price.update.line','import_id',string='Lines to Create',domain=[('state','in',('to_create','error_create','created','create_cancel'))])
    lines_sold = fields.One2many('elneo.supplier.price.update.line','import_id',string='Lines Sold',domain=[('state','in',('to_update','updating_error','updated_pp','updated')),('year_sold_quantity','!=',0)])
    messages = fields.One2many('elneo.supplier.price.update.message','import_id',string='Import Messages')
    increase_price = fields.Float(string='Increase Percent',_compute='_get_increase_percent',help='This is the increase percent from product sold quantities',store=True)
    
    percent_operation_update = fields.Float('Update Operation Progress')
    percent_operation_create = fields.Float('Create Operation Progress')
    
    _defaults={
               'date':lambda *a : datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
               'state':'draft',
               'percent_operation_update':0.0,
               'percent_operation_create':0.0,
               }
    
    _rec_name = 'code'
    
    _order='date desc'
    
    
    def action_draft(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'state':'draft'})
        line_ids = self.pool.get("elneo.supplier.price.update.line").search(cr, uid, [('import_id','in',ids)], context=context)
        self.pool.get("elneo.supplier.price.update.line").action_draft(cr, uid, line_ids, context=context)
        return True
    
    def action_compute_draft(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'state':'draft'})
        return True
    
    def action_computing(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'state':'computing'})
        self.compute_lines(cr, uid, ids, context)
        
        return True
    
    def action_computing_error(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'state':'computing_error'})
        return True
    
    def action_computed(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'state':'computed'})
        return True
    
    def action_updating_purchase_prices(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'state':'updating_pps'})
        self.update_price_lines(cr, uid, ids, context=context)
        return True
    
    def action_updated_purchase_prices(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'state':'updated_pps'})
        return True
    
    def action_updating(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'state':'updating'})
        self.update_sale_price_lines(cr, uid, ids, context=context)
        return True
    
    def action_updating_error(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'state':'updating_error'})
        return True
    
    def action_cancel(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'state':'cancel'})
        return True
    
    def action_done(self,cr,uid,ids,context=None):
        res = False
        if self._update_supplierinfo(cr,uid,ids,context):
            res=True
        if self._check_done(cr, uid, ids, context):
            self.write(cr,uid,ids,{'state':'done'})
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
    def _import_csv(self,cr,uid,ids,context=None):
        res=True
        update = None
        try:
            update_obj = self.pool.get('elneo.supplier.price.update')
            att_obj = self.pool.get('ir.attachment')
            for update in update_obj.browse(cr,uid,ids,context=context):
                
                #if not update.pricelist_file :
                    #self._message(cr, uid, [update.id], _('Impossible to import. The Csv file is not defined!'), context)
                
                att_ids = att_obj.search(cr, uid, [('res_model', '=', 'elneo.supplier.price.update'), ('res_id', '=', update.id)])
                
                if att_ids:
                    pricelist_file = att_obj.browse(cr,uid,att_ids,context=context)[0]
                else:
                    return self._import_csv_big(cr, uid, ids, context)
                
                if not pricelist_file:
                    self._message(cr, uid, [update.id], _('Impossible to import. The Csv file is not defined!'), context)
                csvfile = base64.decodestring(pricelist_file.datas)
                rows = csvfile.split("\r\n")
                total = len(rows)
                
                columns = self._get_columns(row=rows[0])
                
                valid = False
                if update.type == 'elneo_standard':
                    valid = self._validate_columns(cr, uid, update.id,columns, context=context)
                elif update.type == 'landefeld':
                    if (len(columns) == 25):
                        valid = True
                
                # Remove header line        
                rows.pop(0)
                
                if (valid):
                    lines_to_delete = self.pool.get('elneo.supplier.price.update.line').search(cr,uid,[('import_id','=',update.id)],context=context)
                    self.pool.get('elneo.supplier.price.update.line').unlink(cr,uid,lines_to_delete,context=context)
                    for row in rows:
                        if update.type == 'elneo_standard':
                            value = self._get_elneo_standard(cr, uid,row,columns, context)
                        elif update.type == 'landefeld':
                            value = self._get_landefeld(cr, uid,ids,row, context)
                            
                        if value :
                            value['import_id']=update.id
                            result = self.pool.get('elneo.supplier.price.update.line').create(cr,uid,value,context=context)
                else:
                    self._message(cr, uid, ids, _('ERROR : The csv file is not in the expected format'), context)
                
        except Exception,e:
            # We raise Exception but we stay in 'Draft' state - just log the message
            self._message(cr, uid, ids, _('ERROR : ') + unicode(e.message), context)
            raise Warning('Import Error','Unknown error during import!' + unicode(e))
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
    
    #for big pricelists, use sql copy method from file already in filesystem  
    def _import_csv_big(self,cr,uid,ids,context=None):
        
        cr.execute("drop table if exists pricelist_landefeld_full");
        
        cr.execute("""
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
        
        cr.execute("set client_encoding to 'latin1';")
        cr.execute('truncate table pricelist_landefeld_full;')
        cr.execute("copy pricelist_landefeld_full from '/home/openerp/landefeld_pricelist/pricelist.csv' with header delimiter ';' quote '\"' CSV;")
        cr.execute("set client_encoding to 'UTF8';")
        cr.execute("DELETE FROM elneo_supplier_price_update_line WHERE import_id = "+str(ids[0]))
        cr.execute("""INSERT INTO elneo_supplier_price_update_line(
            create_uid, create_date, write_date, write_uid, import_id, 
            product_code, name_tmpl, quantity, public_price, brut_price, net_price, multiply, 
            discount, product_group, weight)
select 1, now(), now(), 1, """+str(ids[0])+""", 
"Artikelnummer", "Bezeichnung1", 
to_number(replace(NULLIF("AbMenge",' '),',','.'),'999999999.99'), 
case when to_number(replace(NULLIF("Preisfaktor",' '),',','.'),'999999999.99') != 1.0 then to_number(replace(NULLIF("Marktpreis",' '),',','.'),'999999999.99')/to_number(replace(NULLIF("Preisfaktor",' '),',','.'),'999999999.99') else to_number(replace(NULLIF("Marktpreis",' '),',','.'),'999999999.99')::float end, 
case when to_number(replace(NULLIF("Preisfaktor",' '),',','.'),'999999999.99') != 1.0 then to_number(replace(NULLIF("Preis",' '),',','.'),'999999999.99')/to_number(replace(NULLIF("Preisfaktor",' '),',','.'),'999999999.99') else to_number(replace(NULLIF("Preis",' '),',','.'),'999999999.99') end, 
case when to_number(replace(NULLIF("Preisfaktor",' '),',','.'),'999999999.99') != 1.0 then to_number(replace(NULLIF("Nettopreis",' '),',','.'),'999999999.99')/to_number(replace(NULLIF("Preisfaktor",' '),',','.'),'999999999.99') else to_number(replace(NULLIF("Nettopreis",' '),',','.'),'999999999.99') end, 
to_number(replace(NULLIF("Preisfaktor",' '),',','.'),'999999999.99'),
to_number(replace(NULLIF("Rabatt",' '),',','.'),'999999999.99'),
"Produktgruppe",
to_number(NULLIF(replace(replace("Gewicht in kg",',','.'),' ',''),''),'999999999.99')
from pricelist_landefeld_full;""")
        return True
        
    
    def _get_landefeld(self,cr,uid,ids,row,context=None):
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
            self._message(cr, uid, ids, _('ERROR : During getting data from Landefeld Line :' + unicode(e)), context)
            res=None
            pass
            
        return res
        
    # If the file type is 'elneo_standard' 
    def _get_elneo_standard(self,cr,uid,row,header,context=None): 
        res = {}
        
        col = self._get_columns(row)
        line_obj = self.pool.get('elneo.supplier.price.update.line')
        
        if col and (len(col) == len (header)):
            i=0
            for head in header :
                if (line_obj._columns[head]._type) == 'Float':
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
    def _validate_columns(self,cr,uid,id,columns,context=None):
        res = True
        line_obj = self.pool.get('elneo.supplier.price.update.line')
        # We parse the update line object and we must find the required columns in the imported file
        for (column,value) in line_obj._columns.iteritems():
            if (value.required and column not in columns):
                self._message(cr, uid, [id.id], _('Impossible to import. Required fields are not present in the file!'), context)
                res = False
                
        return res
    
    
    # Function that launch the thread to import
    def import_lines(self,cr,uid,ids,context=None):
        res=True
        '''
        thread_import = threading.Thread(target=self._import_csv,args=(cr, uid, ids, context))
        thread_import.start()
        '''
        
        self._import_csv(cr, uid, ids, context)

        return res
    
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
            cr.execute("SELECT ail.quantity FROM account_invoice_line ail JOIN account_invoice ai ON ail.invoice_id = ai.id WHERE ail.product_id = " + str(id) + " AND ai.date_invoice >= '" + str(new_date) + "' AND ai.type = 'out_invoice'")
            for tmp in map(lambda x: x[0], cr.fetchall()):
                quantity = quantity + tmp
        #line_ids = self.pool.get('account.invoice.line').search(cr,uid,[('product_id','in',ids),('invoice_id.date_invoice','>=',new_date),('invoice_id.type','=','out_invoice')])
        
        #for line in self.pool.get('account.invoice.line').browse(cr,uid,line_ids,context=context):
            #res=res+line.quantity
        res = quantity
        return res
    
    # Search Method to find products based on supplier product code or on product default code if supplier is the same
    # SQL version to optimize performances
    def _get_supplierinfo(self,cr,uid,line,context=None):
        cr.execute("SELECT id FROM product_supplierinfo WHERE product_code = '" + str(line.product_code) + "' AND name = " + str(line.import_id.supplier_id.id))
        
        res = map(lambda x: x[0], cr.fetchall())
        
        if len(res) == 0 :
            cr.execute("SELECT ps.id FROM product_supplierinfo ps JOIN product_template pt ON ps.product_id = pt.id JOIN product_product pp ON pp.product_tmpl_id = pt.id WHERE pp.default_code = '" + line.product_code + "'")
            res = map(lambda x: x[0], cr.fetchall())
        
        return res
    
    def _get_product_ids(self,cr,uid,ids,context=None):
        res = []
        
        for supplierinfo in self.pool.get('product.supplierinfo').browse(cr,uid,ids,context=context):     
            cr.execute("SELECT pp.id FROM product_product pp WHERE pp.product_tmpl_id = " + str(supplierinfo.product_id.id))       
            for id in map(lambda x: x[0], cr.fetchall()):
                res.append(id)

        return res
    
    def _update_lines(self,cr,uid,ids,properties,context=None):
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
        
        for id in ids :
            sql = "UPDATE elneo_supplier_price_update_line SET " + tmp + " WHERE id="+str(id)
            cr.execute(sql)  
                
        
        
        return res
    
    def _link_products(self,cr,uid,line,product_ids,context=None):
        res = True
        
        sql = "DELETE FROM elneo_supplier_price_update_line_product_rel WHERE update_line_id = " + str(line.id)
        
        cr.execute(sql)
        unique_ids=[]
        [unique_ids.append(item) for item in product_ids if item not in unique_ids]
        for product_id in unique_ids:
            sql = "INSERT INTO elneo_supplier_price_update_line_product_rel(update_line_id,product_id) VALUES (" + str(line.id) + "," + str(product_id) + ")"
            cr.execute(sql)
        
        return res
        
    
    
    
    
    def _set_products(self,cr,uid,line_ids,context=None):
        #insert values in many2many between products and update_line
        #WARNING : this function must be called after _set_suppinfos
        
        res = True
        
        if not id:
            return False
        
        sql =  "delete from elneo_supplier_price_update_line_product_rel where update_line_id in %s"
        
        cr.execute(sql,(tuple(line_ids),))
        
        cr.commit()
        
        sql = """
            insert into elneo_supplier_price_update_line_product_rel 
        select distinct line.id, p.id from elneo_supplier_price_update_line_suppinfo_rel rel
        left join elneo_supplier_price_update_line line on line.id = rel.update_line_id
        left join product_supplierinfo ps 
        left join product_product p on p.product_tmpl_id = ps.product_id
        on ps.id = rel.suppinfo_id
        where line.id in %s"""
        
        cr.execute(sql,(tuple(line_ids),))

        return res
    
    def _set_suppinfos(self,cr,uid,line_ids, context=None):
        res = True
        
        sql =  "delete from elneo_supplier_price_update_line_suppinfo_rel where update_line_id in %s"
        
        cr.execute(sql,(tuple(line_ids),))
        
        cr.commit()
        
        sql = """
        insert into elneo_supplier_price_update_line_suppinfo_rel 
            select line_id,suppinfo_id from
                (select distinct line.id line_id,
                case when suppinfo.id is not null then suppinfo.id else suppinfo_meth2.id end suppinfo_id
                from elneo_supplier_price_update_line line
                    left join elneo_supplier_price_update import on import.id = line.import_id
                    left join product_product product_meth2 on (UPPER(product_meth2.default_code) = UPPER(line.product_code))
                    left join product_supplierinfo suppinfo_meth2 on ((suppinfo_meth2.product_code is null or suppinfo_meth2.product_code = '') and suppinfo_meth2.product_id = product_meth2.product_tmpl_id and suppinfo_meth2.name = import.supplier_id and product_meth2.active)
                    left join product_supplierinfo suppinfo 
                left join product_template suppinfo_product_tmpl 
                    left join product_product suppinfo_product on (suppinfo_product_tmpl.id = suppinfo_product.product_tmpl_id)
                on suppinfo.product_id = suppinfo_product_tmpl.id
                    on (UPPER(suppinfo.product_code) = UPPER(line.product_code) and suppinfo.name = import.supplier_id)
                where line.id in %s and (suppinfo_product.active or suppinfo_product.active is null) and (product_meth2.active or product_meth2 is null)
                order by line.id) suppinfo_not_null WHERE suppinfo_id IS NOT NULL
        """
        
        cr.execute(sql,(tuple(line_ids),))

        return res
    
    def update_lines(self,cr,uid,line_ids,context=None):
        res=True
        
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
                        left join product_product p on p.product_tmpl_id = ps.product_id
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
        
        cr.execute(sql,(tuple(line_ids),))
        
        return res
        
    # Function that :
    # - Makes the link between supplier codes and products
    # - If product exists, change the line state to 'To Update'
    # - If not, change the line state to 'To Create'
    def _compute(self,cr,uid,ids,context=None):
        
        def compute_part(line_ids):
            self._set_suppinfos(cr,uid,line_ids,context=context)
                
            self._set_products(cr,uid,line_ids,context=context)
            
            self.update_lines(cr,uid,line_ids,context=context)
            
            cr.commit()

            line_obj = self.pool.get('elneo.supplier.price.update.line')
            
            lines_to_create = line_obj.search(cr,uid,[('id','in',line_ids),('suppinfo_ids','=',False)],context=context)
            lines_to_update = line_obj.search(cr,uid,[('id','in',line_ids),('suppinfo_ids','!=',False)],context=context)
            
            line_obj.action_to_update(cr, uid, lines_to_update, context)
            line_obj.action_to_create(cr,uid,lines_to_create,context=context)
            
            cr.commit()        
            
            return True
                    
        res = True
        cr = pooler.get_db(self._cr.dbname).cursor()
        update = None
        try:
            for update in self.pool.get('elneo.supplier.price.update').browse(cr,uid,ids,context=context):
                
                all_line_ids = self.pool.get("elneo.supplier.price.update.line").search(cr, uid, [('import_id','=',update.id),('state','=','draft')], context=context)
                all_line_ids_len = len(all_line_ids)
                i = 0
                while i < all_line_ids_len:
                    current_line_ids = all_line_ids[i:i+100]
                    compute_part(current_line_ids)
                    i = i+100

                self.action_computed(cr, uid, update.id, context)
            
        except Exception,e:
            self._message(cr, uid, ids, _('ERROR : During Import lines - ') + unicode(e.message), context)
            self.action_computing_error(cr, uid, ids, context)
            raise Warning('ERROR',_('ERROR : During Import lines - ') + unicode(e.message))
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
    
    # Main function to launch the compute thread
    def compute_lines(self,cr,uid,ids,context=None):
        res=True
        
        if context and context.get('no_thread',False):
            return self._compute(cr, uid, ids, context)
        else:
            thread_compute = threading.Thread(target=self._compute,args=(cr, uid, ids, context))
            thread_compute.start()
        
        return res
        
    # The thread that update the pruchase prices (INSERT)
    def _update_purchase_prices(self,cr,uid,ids,context=None):
        res=True
        cr = pooler.get_db(self._cr.dbname).cursor()
        
        if not (isinstance(ids,list)):
            ids = [ids]
            
        for id in ids :
            try:
                self.pool.get('elneo.supplier.price.update').write(cr,uid,id,{'percent_operation_update':0.0})
                i=0.0
                complete = len(self.pool.get('elneo.supplier.price.update').browse(cr,uid,id).lines_to_update)
                percent = 0.0
                cr.execute("INSERT INTO pricelist_partnerinfo (min_quantity, price, suppinfo_id, brut_price, discount, update_methode, public_price, date) SELECT quantity, net_price,sr.suppinfo_id, brut_price, discount, 'price_list_file', public_price, CURRENT_TIMESTAMP FROM elneo_supplier_price_update_line ul JOIN elneo_supplier_price_update_line_suppinfo_rel sr ON ul.id=sr.update_line_id WHERE import_id = " + str(id) + " AND state='to_update'")
                
                for line in self.browse(cr,uid,id,context=context).lines_to_update:
                    line.action_updated_purchase_price()
                    i=i+1.0
                    percent = (i / complete) * 100
                    self.pool.get('elneo.supplier.price.update').write(cr,uid,id,{'percent_operation_update':percent})
                    cr.commit()
                    
                self.action_updated_purchase_prices(cr, uid, id, context)
                
            except Exception,e:
                self._message(cr, uid, ids, _('ERROR : During Purchase Price Update lines - ') + unicode(e), context)
                self.action_updating_error(cr, uid, ids, context)
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
    def update_price_lines(self,cr,uid,ids,context=None):
        res=True
        
        if context and context.get('no_thread',False):
            return self._update_purchase_prices(cr, uid, ids, context)
        else:
            thread_compute = threading.Thread(target=self._update_purchase_prices,args=(cr, uid, ids, context))
            thread_compute.start()
        
        return res
    
    def _update_sale_prices(self,cr,uid,ids,context=None):
        res = True
        
        cr = pooler.get_db(self._cr.dbname).cursor()
        line_obj = self.pool.get('elneo.supplier.price.update.line')
        
        try:
            for update in self.browse(cr,uid,ids,context=context):
                self.write(cr,uid,update.id,{'percent_operation_update':0.0})
                
                #find all product_ids
                cr.execute("select product_id, line.id from elneo_supplier_price_update_line_product_rel rel left join elneo_supplier_price_update_line line on rel.update_line_id = line.id where line.import_id = %s and line.state = 'updated_pp'",(update.id,))
                product_lines = [{'product_id':product_id, 'line_id':line_id} for (product_id,line_id) in cr.fetchall()]
                
                total = len(product_lines)
                i = 0
                
                
                #for each product, write it to compute sale price, and update line state
                for product_line in product_lines:
                    self.pool.get('product.product').write(cr,uid,product_line['product_id'],{},context=context)
                    
                    line_obj.action_updated(cr,uid, product_line['line_id'], context=context)
                    
                    i = i+1
                    percent = (i / float(total)) * 100.
                    self.pool.get('elneo.supplier.price.update').write(cr,uid,update.id,{'percent_operation_update':percent})
                    
                    
                    cr.commit()
                
                #finally update import state
                update.action_done()
                cr.commit()
                    
        except Exception,e:
            self._message(cr, uid, ids, _('ERROR : During Purchase Price Update lines - ') + unicode(e), context)
            self.action_updating_error(cr, uid, ids, context)
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
    
    def update_sale_price_lines(self,cr,uid,ids,context=None):
        res=True
        
        if context and context.get('no_thread',False):
            return self._update_sale_prices(cr, uid, ids, context)
        else:
            thread_compute = threading.Thread(target=self._update_sale_prices,args=(cr, uid, ids, context))
            thread_compute.start()
        
        return res
    
    def _link_suppinfos(self,cr,uid,line,pricelist_ids,context=None):
        res = False
        
        suppinfo_ids = []
        for pricelist in self.pool.get('pricelist.partnerinfo').browse(cr,uid,pricelist_ids,context=context):
            suppinfo_ids.append(pricelist.suppinfo_id.id)
        
        self.pool.get('elneo.supplier.price.update.line').write(cr,uid,line.id,{'suppinfo_ids':[(6,0,suppinfo_ids)]})
        
        
        return res
    
    # Take all the lines in 'to_create' state and create the corresponding products
    def _create_lines(self,cr,uid,ids,context=None):
        res = True
        
        cr = pooler.get_db(self._cr.dbname).cursor()
        try:
            for update in self.browse(cr,uid,ids,context=context):
                # Initialize the operation percent
                update.write({'percent_operation_create':0.0})
                i=0.0
                complete = len(update.lines_to_create)
                for line in update.lines_to_create:
                    try:
                        # We take only lines to create
                        if line.state =='to_create':
                            values = self._get_values_to_insert(cr,uid,line,context=context)
                            
                            product_created_id = self.pool.get('product.product').create(cr,uid,values,context=context)
                            if product_created_id:
                                template_id = self.pool.get('product.product').browse(cr,uid,product_created_id,context=context).product_tmpl_id.id
                                if template_id:
                                    self._update_translations(cr, uid, line,template_id, context)
                                # Make the link with the product to keep history
                                self._link_products(cr, uid, line, [product_created_id], context)
                                # Creates the pricelist line for the created product for the quantity
                                pricelist_id = self._create_pricelist(cr, uid, line, context)
                                if not pricelist_id:
                                    raise Exception('Error when creating pricelist for the product : ' + str(product_created_id))
                                else:
                                    self._link_suppinfos(cr, uid, line, [pricelist_id], context)
                                line.action_created() 
                                cr.commit()
                        
                    except Exception,e:
                        self._message(cr, uid, ids, _('ERROR : During Create lines - ') + unicode(e), context)
                        self.pool.get('elneo.supplier.price.update.line').browse(cr,uid,line.id,context=context).action_error_create()

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
    def _update_translations(self,cr,uid,line,template_id,context=None):
        res=True
        line_obj = self.pool.get('elneo.supplier.price.update.line')
        if line.name_tmpl:
            if line.name_fr:
                line_obj._update_product_translations(cr,uid,line.name_tmpl,line.name_fr, template_id,'fr_BE')
            if line.name_nl:
                line_obj._update_product_translations(cr,uid,line.name_tmpl,line.name_nl, template_id,'nl_BE')
            if line.name_de:
                line_obj._update_product_translations(cr,uid,line.name_tmpl,line.name_de, template_id,'de')
            if line.name_en:
                line_obj._update_product_translations(cr,uid,line.name_tmpl,line.name_en, template_id,'en_US')
        
        
        return res
    
    # Create the product pricelist information
    def _create_pricelist(self,cr,uid,line,context=None):
        res = None
        for product in self.pool.get('elneo.supplier.price.update.line').browse(cr,uid,line.id,context=context).product_ids:
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
            
            suppinfo_id = self.pool.get('product.supplierinfo').create(cr,uid,value,context=context)
            
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
                

                pricelist_id = self.pool.get('pricelist.partnerinfo').create(cr,uid,value,context=context)
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
    def _get_values_to_insert(self,cr,uid,line,context=None):
        res={}
        
        if line.product_code:
            res['default_code']=line.product_code
            res['list_price']=line.public_price
            res['public_price']=line.public_price
        if line.product_category_id:
            res['categ_id']=line.product_category_id.id
        if line.name_tmpl:
            res['name']=line.name_tmpl
        if line.weight:
            res['weight_net']=line.weight
 
        return res
   
    def _message(self,cr,uid,ids,message,context=None):
        res = True
        
        for update in self.pool.get('elneo.supplier.price.update').browse(cr,uid,ids,context=context):
            self.pool.get('elneo.supplier.price.update.message').create(cr,uid,{'import_id':update.id,'message':message,'date':datetime.now()})
            
        return res
    
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
    
    #Update products translations
    def _update_product_translations(self, cr, uid,name_tpl, translation, product_template_id,lang, context=None):
        if not context:
            context = {}
        
        ir_translation_ids = self.pool.get('ir.translation').search(cr,uid,[('lang','=',lang),('name','=','product.template,name'),('res_id','=',product_template_id)])
        
        if ir_translation_ids:
            for ir_translation_id in ir_translation_ids:
                self.pool.get('ir.translation').write(cr, uid, ir_translation_id, {
                                                                                   'src':name_tpl,
                                                                                   'value':translation,
                                                                                   }, context)
        else:
            self.pool.get('ir.translation').create(cr, uid, {
                                                             'name':'product.template,name',
                                                             'lang':lang,
                                                             'src':name_tpl,
                                                             'res_id':product_template_id,
                                                             'type':'model',
                                                             'value':translation,
                                                             }, context)
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
    
    def action_draft(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'state':'draft'})
        return True
    
    def action_to_update(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'state':'to_update'})
        return True
    
    def action_to_create(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'state':'to_create'})
        return True
    
    def action_error_create(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'state':'error_create'})
        return True
    
    def action_error_update(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'state':'error_update'})
        return True
    
    def action_updating(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'state':'updating'})
        return True
    
    def action_created(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'state':'created'})
        return True
    
    def action_updated_purchase_price(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'state':'updated_pp'})
        return True
    
    def action_updated(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'state':'updated'})
        return True
    
    def action_create_cancel(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'state':'create_cancel'})
        return True

elneo_supplier_price_update_line()


class elneo_supplier_price_update_message(models.Model):
    _name='elneo.supplier.price.update.message'
    
    import_id = fields.Many2one('elneo.supplier.price.update','Import')
    message = fields.Text(string='Message',readonly=True)
    date = fields.Datetime(string='Date',readonly=True)
    
elneo_supplier_price_update_message()


