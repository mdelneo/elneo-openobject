from openerp import models, fields,api
from openerp.tools.translate import _
from openerp.exceptions import Warning

class product_product(models.Model):
    _inherit = 'product.product'
    
    alias = fields.Char(string="Alias", size=255, translate=False)
    qty_available_text = fields.Char(compute='_product_available_text')
    barcode_number = fields.Char('Barcode number', size=7, default=lambda obj: obj.env['ir.sequence'].get('product.barcode'), groups='stock.group_stock_manager')

    
    def check_seller_ids(self, vals):
        if not self._context.get('copy',False) and (vals and ((not 'seller_ids' in vals) or not vals['seller_ids'])) and not self.seller_ids:
            raise Warning(_('You must add at least one supplier to the product.'))
        return

    @api.multi
    def write(self, vals):
        self.check_seller_ids(vals)
        return super(product_product, self).write(vals)
    
    @api.model
    def create(self, vals):
        self.check_seller_ids(vals)
        return super(product_product, self).create(vals)
    
    @api.multi
    def _product_available_text(self):
        for product in self:
            product.qty_available_text = 'A: '+str(product.with_context(location=[15]).qty_available)+' | W: '+str(product.with_context(location=[16]).qty_available) 

    
    def _auto_init(self,cr,args):
        res = super(product_product, self)._auto_init(cr, args)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'product_product_alias_ext_name_index\'')
        if not cr.fetchone():
            cr.execute('CREATE INDEX product_product_alias_ext_name_index ON product_product (alias, default_code)')
        return res
    
    
    @api.one
    def copy(self, default=None):
        if default is None:
            default = {}
        
        default_code = self.default_code
        if not default_code:
            default_code = ''    
        
        #add suffix to default_code on duplicate
        suffix = ' - copy'
        nb = len(self.search([('default_code','=',default_code+suffix)]))
        if nb>=1:
            suffix = suffix+' ('+str(nb)+')'
        default.update({'default_code':default_code+suffix})
        
        #new barcode
        default['barcode_number'] = self.env['ir.sequence'].get('product.barcode')
        
        return super(product_product, self.with_context(copy=True)).copy(default)
    
    
    def search_ext_name(self, name, args):
        text_to_search = None
        if args:
            text_to_search = args
       
                
        self.env.cr.execute("""
            select distinct product_product.id from product_product left join product_template on product_product.product_tmpl_id = product_template.id 
            left join product_supplierinfo on product_supplierinfo.product_tmpl_id = product_template.id 
            left join ir_translation on ir_translation.res_id = product_template.id and ir_translation.name = 'product.template,name' 
            where
            product_product.default_code ilike '%"""+text_to_search+"""%'
            or product_product.alias ilike '%"""+text_to_search+"""%' 
            or product_supplierinfo.product_name ilike '%"""+text_to_search+"""%' 
            or product_supplierinfo.product_code ilike '%"""+text_to_search+"""%'
            or ir_translation.value ilike '%"""+text_to_search+"""%' 
            or product_template.name ilike '%"""+text_to_search+"""%'
;""")
        
        res = self.env.cr.fetchall()
        return [('id', 'in', [x[0] for x in res])]
    
    @api.one
    def get_ext_name(self,field_name, arg):
        result = {}
        #products = self.browse(cr, uid, ids, context)
        #for product in products:        
        if self.alias:
            new_name = self.default_code+" "+self.alias
        else:
            new_name = result[self.id] = self.default_code
            
        for seller in self.seller_ids:
            if seller.product_code:
                new_name += " "+seller.product_code
        
        result[self.id] = new_name
                
        return result
    
    
    
    
    
class product_template(models.Model):
    _inherit = 'product.template'
    
    _defaults = {
        'sale_ok':True,
        'purchase_ok':True
    }
    
    def _auto_init(self,cr,args):
        res = super(product_template, self)._auto_init(cr, args)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'product_template_ext_name_index\'')
        if not cr.fetchone():
            cr.execute('CREATE INDEX product_template_ext_name_index ON product_template (name)')
        return res
    
    

    type = fields.Selection([('product', 'Stockable Product'),('consu', 'Consumable'),('service','Service')], 'Product Type', required=True,default='product', help="Consumable are product where you don't manage stock, a service is a non-material product provided by a company or an individual.")
    
    list_price2 = fields.Float('Sale price', related='list_price')
    
class pricelist_partnerinfo(models.Model):
    _inherit = 'pricelist.partnerinfo'
    suppinfo_id = fields.Many2one(index=True)
