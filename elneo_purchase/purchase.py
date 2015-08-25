from openerp import models, fields, api


class base_config_settings(models.TransientModel):
    _inherit = 'purchase.config.settings'

    default_purchase_type_id = fields.Many2one('purchase.order.type',string='Default purchase type',help='The Default purchase type proposed on new sale purchase order')
   
    @api.multi
    def set_purchase_default_purchase_type(self):
        self.env['ir.config_parameter'].set_param('elneo_purchase.default_purchase_type_id',repr(self.default_purchase_type_id.id))
        
    
    @api.model
    def get_default_purchase_type_id(self,fields):
        default_purchase_type_id = self.env['ir.config_parameter'].get_param('elneo_purchase.default_purchase_type_id',False)
        if default_purchase_type_id !='False':
            default_purchase_type_id = int(default_purchase_type_id)
        else:
            default_purchase_type_id = False
        return {'default_purchase_type_id':default_purchase_type_id}

class purchase_order_type(models.Model):
    _name = 'purchase.order.type'
    
    name = fields.Char('Name',size=255,translate=True,required=True)
    

purchase_order_type()

class purchase_order(models.Model):
    
    _inherit='purchase.order'
    
    purchase_type_id = fields.Many2one('purchase.order.type','Purchase Type')
    sale_ids = fields.Many2many('sale.order', 'purchase_sale_rel', 'purchase_id', 'sale_id', 'Sales')
    
    @api.model
    def default_get(self, fields_list):
        res = super(purchase_order,self).default_get(fields_list)
        purchase_type = self.env['ir.config_parameter'].get_param('elneo_purchase.default_purchase_type_id',False)
        if purchase_type:
            purchase_type_id = int(purchase_type)
            res['purchase_type_id'] = purchase_type_id
        return res
    
    
    @api.multi
    def copy(self, default=None):
        if not default:
            default = {}
        default['sale_ids'] = None
        return super(purchase_order, self).copy(default)
    
purchase_order()

class purchase_order_line(models.Model):
    _inherit='purchase.order.line'
    
    sale_line_ids = fields.Many2many('sale.order.line', 'purchase_line_sale_line_rel', 'purchase_line_id', 'sale_line_id', 'Sale lines')
    
    @api.multi
    def copy(self, default=None):
        if not default:
            default = {}
        default['sale_line_ids'] = None
        return super(purchase_order_line, self).copy(default)    
    
purchase_order_line()


class procurement_order(models.Model):
    
    _inherit = 'procurement.order'
    
    @api.multi
    def make_po(self):
        res = super(procurement_order,self).make_po()
        #link sales with purchase in accordance with procurement group
        for procurement in self:
            if procurement.purchase_line_id and procurement.group_id:
                for other_procurement in procurement.group_id.procurement_ids:
                    if other_procurement.sale_line_id:
                        other_procurement.sale_line_id.order_id.write({'purchase_ids':[(4,procurement.purchase_id.id)]})
                        other_procurement.sale_line_id.write({'purchase_line_ids':[(4,procurement.purchase_line_id.id)]})
        return res
