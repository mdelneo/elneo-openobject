from openerp import models, fields, api
        
class product_product(models.Model):
    _inherit = 'product.product'
    
    def _purchases_count(self):
        self._cr.execute('select product_id, count(distinct order_id) from purchase_order_line where product_id in (%s) group by product_id',(tuple([p.id for p in self]),))
        req_res = self._cr.fetchall()
        res = {}
        for req_res_line in req_res:
            res[req_res_line[0]] = req_res_line[1]
        for product in self:
            if product.id in res:
                product.purchases_count = res[product.id]
            else:
                product.purchases_count = 0
        return res
            
    purchases_count = fields.Integer(compute='_purchases_count', string='# Purchases')
    

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


class purchase_order(models.Model):
    
    _inherit='purchase.order'
    
    
    STATE_SELECTION = [
        ('draft', 'Draft PO'),
        ('confirmed', 'Waiting Approval'),
        ('approved', 'Purchase Confirmed'),
        ('except_picking', 'Shipping Exception'),
        ('except_invoice', 'Invoice Exception'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ]
    
    
    purchase_type_id = fields.Many2one('purchase.order.type','Purchase Type')
    state = fields.Selection(STATE_SELECTION, 'Status', readonly=True)

    #super method is in old api so we can't browse res so I rewrite the method in new API    
    @api.multi
    def action_picking_create(self):
        for order in self:
            picking_vals = {
                'picking_type_id': order.picking_type_id.id,
                'partner_id': order.partner_id.id,
                'date': order.date_order,
                'origin': order.name+' '+','.join([so.name for so in order.sale_ids])
            }
            picking = self.env['stock.picking'].create(picking_vals)
            order._create_stock_moves(order, order.order_line, picking.id)
        return picking.id
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(purchase_order,self).default_get(fields_list)
        purchase_type = self.env['ir.config_parameter'].get_param('elneo_purchase.default_purchase_type_id',False)
        if purchase_type:
            purchase_type_id = int(purchase_type)
            res['purchase_type_id'] = purchase_type_id
            
        if self.env.user.default_warehouse_id:
            res['picking_type_id']=self.env['stock.picking.type'].search([('warehouse_id','=',self.env.user.default_warehouse_id.id)],limit=1).id
        return res
    
    @api.multi
    def write(self,vals):
        if self.env.context.get('from_procurement',False):
            if 'origin' in vals:
                position = vals['origin'].find(self.origin)
                if position != -1:
                    #If there is a trailing string
                    if (len(vals['origin']) > len (self.origin)):
                        if (vals['origin'][len(self.origin)+1:len(vals['origin'])]).find(self.origin) != -1:
                            #If the trailing string is equals to the original string
                            del vals['origin']
                   
        return super(purchase_order,self).write(vals)
    
    
class ProcurementOrder(models.Model):
    _inherit='procurement.order'
    
    @api.multi
    def make_po(self):
        return super(ProcurementOrder,self.with_context(from_procurement=True)).make_po()
        
        