from openerp import models, fields,api
from openerp.exceptions import ValidationError
import time
from openerp.tools.translate import _


class base_config_settings(models.TransientModel):
    _inherit = 'sale.config.settings'

    default_carrier_id = fields.Many2one('delivery.carrier',string='Default delivery',help='The Default carrier proposed on new sale order')
   
    @api.multi
    def set_sale_default_carrier(self):
        self.env['ir.config_parameter'].set_param('delivery_method_auto.default_carrier_id',repr(self.default_carrier_id.id))
        
    
    @api.model
    def get_default_carrier(self,fields):
        default_carrier_id = self.env['ir.config_parameter'].get_param('delivery_method_auto.default_carrier_id',False)
        if default_carrier_id !='False':
            default_carrier_id = int(default_carrier_id)
        else:
            default_carrier_id = False
        return {'default_carrier_id':default_carrier_id}

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    @api.onchange('carrier_id')
    def on_change_carrier_id(self):
        if not self.carrier_id:
            return
        carrier_product_ids = [c.product_id.id for c in self.env['delivery.carrier'].search([])]
        for line in self.order_line:
            if line.product_id and line.product_id.id in carrier_product_ids: #we should use is_delivery fields but it doesn't works
                delivery_line = self.get_delivery_line()
                if delivery_line:
                    line.update(delivery_line)
                return
        delivery_line = self.get_delivery_line()
        if delivery_line:
            self.order_line |= self.order_line.new(delivery_line)
            
    def get_delivery_line(self):
        grid_id = self.carrier_id.grid_get(self.partner_shipping_id.id)
        if not grid_id:
            raise ValidationError(_('No grid matching for this carrier!'))
        if self.state not in ('draft', 'sent'):
            raise ValidationError(_('The order state have to be draft to add delivery lines.'))
        grid = self.env['delivery.grid'].browse(grid_id)
        taxes = grid.carrier_id.product_id.taxes_id
        fpos = self.fiscal_position or False
        if not fpos:
            return False
        
        cost_price = self.carrier_id.product_id.cost_price
        
        taxes = fpos.map_tax(taxes)
        price_unit = grid.get_price(self, time.strftime('%Y-%m-%d'))
        if price_unit:
            price_unit = price_unit[0]
        if self.company_id.currency_id.id != self.pricelist_id.currency_id.id:
            price_unit = self.company_id.currency_id.with_context(dict(self._context or {}, date=self.date_order)).compute(self.pricelist_id.currency_id.id,price_unit)
        #create the sale order line
        return {
            'name': grid.carrier_id.name,
            'product_uom_qty': 1,
            'product_uom': grid.carrier_id.product_id.uom_id.id,
            'product_id': grid.carrier_id.product_id.id,
            'price_unit': price_unit,
            'purchase_price':cost_price,
            'tax_id': [(6, 0, [taxe.id for taxe in taxes])],
            'is_delivery': True
        }     
    
    
    @api.multi
    def onchange_partner_id(self, partner):
        result = super(sale_order, self).onchange_partner_id(partner)
        if partner:
            partner_obj = self.env['res.partner'].browse(partner)
            if not partner_obj.property_account_position:
                if not 'warning' in result:
                    result['warning'] = {}
                title = _('Fiscal position missing')
                message = _('Please add fiscal position to partner %s.')%(partner_obj.name,)
                if 'title' in result['warning']:
                    result['warning']['title'] = result['warning']['title'] + title or title
                else:
                    result['warning']['title'] = title
                
                if 'message' in result['warning']:
                    result['warning']['message'] = result['warning']['message'] + message or message
                else:
                    result['warning']['message'] = message
            
            
            carrier_id = self.env['ir.config_parameter'].get_param('delivery_method_auto.default_carrier_id',False)
            if carrier_id == 'False':
                carrier_id = None
            if carrier_id:
                carrier_id = int(carrier_id)
            result['value']['carrier_id'] = carrier_id
        return result
    
    
class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
