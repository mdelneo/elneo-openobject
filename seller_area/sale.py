# -*- coding: utf-8 -*-
from openerp import models, fields, api

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    @api.model
    def _find_sale_man_id(self,partner_shipping_id):
        if not partner_shipping_id or not self.env.user.default_section_id:
            return None
        
        corr_obj = self.env['res.user.zip.rel']
        exception_obj = self.env['res.partner.sale.exception']
        addr = self.env['res.partner'].browse(partner_shipping_id)
        if addr.parent_id:
            partner = addr.parent_id
        else:
            partner = addr
            
        partner_exceptions = exception_obj.search([('partner', '=', partner.id), ('department', '=', self.env.user.default_section_id.id)])
        if partner_exceptions:
            sale_exception = partner_exceptions[0]
            return sale_exception.user.id
        
        corr_ids = corr_obj.search([('zip_min', '<=', addr.zip), ('zip_max', '>=', addr.zip), ('department', '=', self.env.user.default_section_id.id)])
        if corr_ids:
            corr = corr_ids[0]
            return corr.user.id
        return None
    
    
    @api.multi
    def onchange_delivery_id(self,company_id, partner_id, partner_shipping_id, fiscal_position):
        res = super(sale_order,self).onchange_delivery_id(company_id, partner_id, partner_shipping_id, fiscal_position)
        
        res['value'].update({'user_id': self._find_sale_man_id(partner_shipping_id),
                             'section_id' : self.env.user.default_section_id.id
                             })
        
        return res

sale_order()

