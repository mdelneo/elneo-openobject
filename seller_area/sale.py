# -*- coding: utf-8 -*-
from openerp import models, fields, api



class sale_order(models.Model):
    _inherit = 'sale.order'
    
    '''
    def onchange_partner_id(self, cr, uid, ids, part):
        res = super(sale_order, self).onchange_partner_id(cr, uid, ids, part)
        is_seller = self.pool.get("hr.employee").search(cr, uid, [('user_id','=',uid), ('job_id','=',11)])
        if is_seller and res and res.has_key("value") and res['value'].has_key("partner_order_id"):
            res['value']['quotation_address_id'] = res["value"]["partner_order_id"]
        if not part and res and res.has_key("value"):
            res['value']['quotation_address_id'] = None
        return res
    '''    
    
    def _find_sale_man_id(self):
        if not self.partner_shipping_id or not self.env.user.default_section_id:
            return None
        
        corr_obj = self.env['res.user.zip.rel']
        exception_obj = self.env['res.partner.sale.exception']
       
        partner_exceptions = exception_obj.search([('partner', '=', self.partner_id.id), ('department', '=', self.env.user.default_section_id.id)])
        if partner_exceptions:
            sale_exception = partner_exceptions[0]
            return sale_exception.user.id
        
        corr_ids = corr_obj.search([('zip_min', '<=', self.partner_id.zip), ('zip_max', '>=', self.partner_id.zip), ('department', '=', self.env.user.default_section_id.id)])
        if corr_ids:
            corr = corr_ids[0]
            return corr.user.id
        return None
    
    '''
    def onchange_quotation_address_id(self, cr, uid, ids, quotation_address_id):
        if quotation_address_id:
            return {'value':{'partner_order_id':quotation_address_id}}
        return {}
    '''
    
    
    @api.model
    @api.onchange('partner_shipping_id')
    def onchange_shipping_id(self):
    
       self.user_id = self._find_sale_man_id()
       self.section_id = self.env.user.default_section_id.id,

sale_order()

