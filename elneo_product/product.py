from openerp import models, fields

class product_template(models.Model):
    _inherit = 'product.template'
    

    type = fields.Selection([('product', 'Stockable Product'),('consu', 'Consumable'),('service','Service')], 'Product Type', required=True,default='product', help="Consumable are product where you don't manage stock, a service is a non-material product provided by a company or an individual.")
    
product_template()