from openerp import models, fields,api
from openerp.exceptions import ValidationError
import time
from openerp.tools.translate import _

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    @api.cr_uid_ids_context
    def onchange_partner_id_with_shop_sale(self,cr,uid,ids, partner, shop_sale,context=None):
        if context is None:
            context={}
        result = super(sale_order, self).onchange_partner_id(cr,uid,ids,partner,context=context)
        
        #for shop sale, don't set default carrier_id
        if shop_sale and 'value' in result and 'carrier_id' in result['value']:
            del result['value']['carrier_id']
        return result
    
