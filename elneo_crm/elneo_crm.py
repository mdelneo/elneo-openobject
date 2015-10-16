# -*- coding: utf-8 -*-
from openerp import models,fields,api
from openerp.exceptions import ValidationError

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    ref = fields.Char('Reference', size=10,index=True, readonly=True)
    alias = fields.Char('Alias', size=255,index=True)
    sales_count = fields.Integer('Number of sales', compute='_get_sales_count')
    
    type = fields.Selection([('contact', 'Contact'),('delivery', 'Shipping'), ('invoice', 'Invoice')], string='Address Type')
    
    
    def action_view_sales(self, cr, uid, ids, context=None):
        result = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'sale.action_orders', raise_if_not_found=True)
        result = self.pool['ir.actions.act_window'].read(cr, uid, [result], context=context)[0]
        result['domain'] = "[('partner_id','in',[" + ','.join(map(str, ids)) + "])]"
        result['context'] = {'search_default_my_sale_orders_filter': 0}
        return result
    
    def _get_sales_count(self):
        self._cr.execute('select partner_id, count(id) from sale_order where partner_id in %s group by partner_id',(tuple([p.id for p in self]),))
        req_res = self._cr.fetchall()
        res = {}
        for req_res_line in req_res:
            res[req_res_line[0]] = req_res_line[1]
        for partner in self:
            if partner.id in res:
                partner.sales_count = res[partner.id]
            else:
                partner.sales_count = 0
        return res
            
    
    @api.constrains('ref')
    def _check_ref(self):
        #Mother companies must have reference
        if (not self.parent_id and not self.ref):
            raise ValidationError("You must fill in the reference for this partner!")
        
        sames = self.search([('active','=',True),('parent_id','=',False),('ref','=',self.ref),('id','!=',self.id)])
        if (sames):
            raise ValidationError("There is partner with the same reference! Please change it or go to the good partner.\n\n%s" % (sames[0].name))
            
    def _get_default_is_company(self):
        return self._context.get('force_is_company', False)
    
    
    @api.multi
    def _sale_order_count(self):
        for partner in self:
            if not partner.is_company:
                partner.sale_order_count = 0
            else:
                count = self.env['sale.order'].search_count([('partner_id','=',partner.id),('state','not in',['cancel','draft'])])
                count_progress = self.env['sale.order'].search_count([('partner_id','=',partner.id),('state','not in',['cancel','draft','done'])])
                partner.sale_order_count = str(count)+' ('+str(count_progress)+')'
            
            
    @api.multi
    def _purchase_order_count(self):
        for partner in self:
            if not partner.is_company:
                partner.purchase_order_count = 0
            else:
                count = self.env['purchase.order'].search_count([('partner_id','=',partner.id),('state','not in',['cancel','draft'])])
                count_progress = self.env['purchase.order'].search_count([('partner_id','=',partner.id),('state','not in',['cancel','draft','done'])])
                partner.purchase_order_count = str(count)+' ('+str(count_progress)+')'
            
            
    @api.multi
    def _supplier_invoice_count(self):
        for partner in self:
            if not partner.is_company:
                partner.supplier_invoice_count = 0
            else:
                count = self.env['account.invoice'].search_count([('type','=','in_invoice'),('partner_id','=',partner.id),('state','not in',['cancel'])])
                count_progress = self.env['account.invoice'].search_count([('type','=','in_invoice'),('partner_id','=',partner.id),('state','not in',['cancel','open','paid'])])
                partner.supplier_invoice_count = str(count)+' ('+str(count_progress)+')'
            

    sale_order_count = fields.Char(compute='_sale_order_count', string='# of Sales Order', size=255)
    is_company = fields.Boolean('Is a company', default=_get_default_is_company)
    purchase_order_count = fields.Char(compute='_purchase_order_count', string='# of Purchase Order', size=255)
    supplier_invoice_count = fields.Char(compute='_supplier_invoice_count', string='# Supplier Invoices', size=255)