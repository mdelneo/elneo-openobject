from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
from openerp import models,fields,api
from operator import itemgetter
import re



class product_property_unit(models.Model):
    _name = 'product.property.unit'
    _description = 'Unit of properties'
    
    name = fields.Char('Name', size=50, translate=True)
    
product_property_unit()

class product_property_category(models.Model):
    _name = 'product.property.category'
    _description = 'A category of properties'
    
    product_category_id = fields.Many2one('product.category', 'Product category')
    name = fields.Char('Name', size=100, translate=True)
    sequence = fields.Integer('Sequence')
    product_properties = fields.One2many('product.property', 'product_property_category_id', 'Properties')
            
product_property_category()

class product_property(models.Model):
    _name = 'product.property'
    _description = 'Technical data'
    
    product_property_category_id = fields.Many2one('product.property.category', 'Category')
    product_property_values = fields.One2many('product.property.value', 'product_property_id', 'Assigned properties') 
    name = fields.Char('Name', size=1024, translate=True)
    sequence = fields.Integer('Sequence')
    default_value = fields.Text("Default value", translate=True) 
    product_category_id = fields.Many2one('product.category', related="product_property_category_id.product_category_id", string="Product Category", readonly=True) 
    unit_id = fields.Many2one('product.property.unit', string="Unit")
    
    @api.multi
    def write(self, vals):
        for pp in self:
            for property_value in pp.product_property_values:
                if 'name' in vals and property_value.use_default_name:
                    property_value.name = vals['name']
                if 'default_value' in vals and property_value.use_default_name:
                    property_value.name = vals['default_value']
        return super(product_property, self).write(vals)
    
product_property()
    
class product_property_value(models.Model):
    _name = 'product.property.value'
    _description = 'A property assigned to a product'
    _order = 'sequence'
    
    @api.onchange('product_property_id')
    def onchange_product_property_id(self):
        if self.product_property_id:
            self.product_property_category_id = self.product_property_id.product_property_category_id
            self.use_default_value = True
            self.use_default_name = True
            self.use_default_unit = True
    
    def get_used(self):
        res = {}
        for prop in self:
            if prop.use_default_name:
                prop.used_name = prop.default_name
            else:
                prop.used_name = prop.name
            if prop.use_default_value:
                prop.used_value = prop.default_value
            else:
                prop.used_value = prop.value
            if prop.default_unit_id:
                prop.used_unit_id = prop.default_unit_id
            elif prop.unit_id:
                prop.used_unit_id = prop.unit_id
        return res
        
    product_id = fields.Many2one('product.product', 'Product', ondelete='cascade') 
    product_property_id = fields.Many2one('product.property', 'Property', ondelete='cascade', select=True) 
    product_property_category_id = fields.Many2one('product.property.category', 'Property Category', ondelete='cascade')
    sequence = fields.Integer('Sequence')
    product_category_id = fields.Many2one('product.category', string='Product category',select=True)
    name = fields.Char('Name', size=1024, translate=True)
    default_name = fields.Char(related='product_property_id.name', string='Name', readonly=True)
    use_default_name = fields.Boolean("Use default name")
    used_name = fields.Char(compute='get_used', method=True, string="Used name", type="char", multi="get_used")
    value = fields.Text('Value', translate=True)
    default_value = fields.Text(related='product_property_id.default_value', string="Value", readonly=True)
    use_default_value = fields.Boolean("Use default value")
    used_value = fields.Text(compute='get_used', method=True, string="Used value", type="text", multi="get_used")
    unit_id = fields.Many2one('product.property.unit', string="Unit")
    default_unit_id = fields.Many2one(related='product_property_id.unit_id', type="many2one", relation='product.property.unit', string="Unit", readonly=True)
    use_default_unit = fields.Boolean("Use default unit")
    active1 = fields.Boolean('Active', default=True)
    
product_property_value()


class sale_quotation_property(models.Model):
    _name = 'sale.quotation.property'
    _description = 'properties for quotation'
    _order = 'sequence'
    
    sale_order_line_id = fields.Many2one('sale.order.line', 'Sale order line')
    category = fields.Char('Category', size=100)
    name = fields.Char('Name', size=100)
    sequence = fields.Integer('Sequence')
    value = fields.Text('Value')
    unit = fields.Text('Unit')
    
sale_quotation_property()

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    
    @api.one
    @api.onchange('product_id')
    def update_sale_quotation_properties(self):
        def convert_product_property_value_to_quotation_property(product_property_value):
            unit = ''
            if product_property_value.use_default_unit:
                if product_property_value.default_unit_id:
                    unit = product_property_value.default_unit_id.name
            elif product_property_value.unit_id:
                unit = product_property_value.unit_id.name
                
            
            res = {
                "category" : product_property_value.product_property_category_id.name, 
                "name":product_property_value.used_name, 
                "sequence" : product_property_value.sequence,  
                "value":product_property_value.used_value, 
                "unit":unit
            }
                
            return res 
           
        sale_quotation_properties = []
        if self.product_id:     
            context = {'lang': self.order_id.partner_id.lang, 'partner_id': self.order_id.partner_id.id, 'product_id':self.product_id}       
            ppvs = self.env["product.property.value"].search([('product_id','=',self.product_id.id)])
            for ppv in ppvs:
                if ppv.active1:
                    sqp = convert_product_property_value_to_quotation_property(ppv)
                    sale_quotation_properties.append(sqp)
        
        self.sale_quotation_properties = sale_quotation_properties
        
    
    sale_quotation_properties = fields.One2many('sale.quotation.property', 'sale_order_line_id', string="Properties")
sale_order_line()

class product_product(models.Model):
    _inherit = 'product.product'
    
    product_property_values = fields.One2many('product.property.value', 'product_id', string="Properties")
product_product()

class product_category(models.Model):
    _inherit = 'product.category'
    product_property_categories = fields.One2many('product.property.category', 'product_category_id', string="Property categories")
    
    
    #fill product_property_value of children of current product category
    @api.multi
    def action_fill(self):
        #find all children
        for parent_categ_id in self:
            children_cat = self.get_children_cat([parent_categ_id])
            categories = [parent_categ_id]
            categories.extend(children_cat)
            
        products = self.env["product.product"].search([('categ_id','in',[c.id for c in categories])])
        product_property_category_pool= self.env["product.property.category"]
        product_property_value_pool = self.env["product.property.value"]
        
                   
        for product in products:
            
            #find all categories of current product, begin with upper category
            categ = product.categ_id
            categs = [categ.id]
            
            while categ.parent_id:
                categ = categ.parent_id
                categs.append(categ.id)                    
            categs.reverse()                
            
            product_property_categories = product_property_category_pool.search([('product_category_id', 'in', categs)], order='sequence,id')
            
            seq = 0
            for ppc in product_property_categories:
                for pp in ppc.product_properties:                        
                    seq = seq+1
                    existing_values = product_property_value_pool.search([('product_id','=',product.id),('product_property_id','=',pp.id)], order='sequence,id')
                    if len(existing_values) == 0:
                        product_property_value_pool.create({
                            'product_id':product.id,
                            'product_property_category_id':pp.product_property_category_id.id, 
                            'product_property_id':pp.id,
                            'use_default_value':True,
                            'use_default_name':True, 
                            'use_default_unit':True,  
                            'sequence':seq
                        })
                    else:
                        existing_values.write({'sequence':seq})
            
    #Recursive function to get all children categories of category passed by parameter
    def get_children_cat(self, parent_cats, children=[]):
        new_children = self.env["product.category"].search([("parent_id",'in',[p.id for p in parent_cats])])
        if len(new_children) > 0:     
            children.extend(new_children)       
            self.get_children_cat(new_children, children)
        return children
    
    
product_category()

