# -*- coding: utf-8 -*-
from openerp import models,fields,api
from openerp.exceptions import ValidationError, Warning
from openerp.tools.translate import _

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    @api.model
    def default_get(self, fields_list):
        res = super(res_partner, self).default_get(fields_list)
        if self._context.get('is_company',False):
            res['is_company'] = True 
        return res

class product_product(models.Model):
    _inherit = 'product.product'
    
    @api.model
    def default_get(self, fields_list):
        if self._context.get('default_name'):
            self = self.with_context(default_name=None,default_default_code=self._context.get('default_name'))
        res = super(product_product, self).default_get(fields_list)
        return res
    
    def _sales_count(self):
        self._cr.execute('select product_id, count(distinct order_id) from sale_order_line where product_id in (%s) group by product_id',(tuple([p.id for p in self]),))
        req_res = self._cr.fetchall()
        res = {}
        for req_res_line in req_res:
            res[req_res_line[0]] = req_res_line[1]
        for product in self:
            if product.id in res:
                product.sales_count = res[product.id]
            else:
                product.sales_count = 0
        return res
            
    sales_count = fields.Integer(compute='_sales_count', string='# Sales')

class product_category(models.Model):
    _inherit = 'product.category'
    
    stat_on_invoice_date_default = fields.Boolean('Stats on invoice date by default', help="If this box is checked, if a sale order contains a product of this category, when it will be confirmed, sale order 'Stats on invoice date' box will be checked.")

class procurement_order(models.Model):
    _inherit = 'procurement.order'
    
    sale_line_id = fields.Many2one('sale.order.line', index=True)
    
    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        new_procurement = super(procurement_order, self).create(vals)
        
        jit = False
        if vals.get('sale_line_id'):
            line = self.env['sale.order.line'].browse(vals['sale_line_id'])
            jit = line.order_id.jit
            
        if jit:
            new_procurement.run()
            new_procurement.check()
            
        return new_procurement
        
    @api.multi
    def make_po(self):
        #to force new purchase order creation, when we call "make po", say to search function of purchase order that only purchase order of current sale exists
        #to do it we pass make_po = True to the context
        self = self.with_context(make_po=self._context.get('make_po',{'group_id':self.group_id.id}))
        res = super(procurement_order, self).make_po()
        return res
    

class purchase_order(models.Model):
    _inherit = 'purchase.order'
    
    
    @api.returns('self')
    def search(self, cr, uid, args,
               offset=0, limit=None, order=None, context=None, count=False):
        #if make_po = True, we simulate that only purchase order of current sale exists, to force new purchase order creation
        if context.get('make_po',False):
            proc_ids=self.pool.get('procurement.order').search(cr,uid,[('group_id','=',context.get('make_po')['group_id'])],context=context)
            procs = self.pool.get('procurement.order').browse(cr,uid,proc_ids,context=context)
            args.append(('id','in',procs.mapped('purchase_id.id')))
            #args.append(('sale_ids.procurement_group_id','=',context.get('make_po')['group_id']))
        res = super(purchase_order, self).search(cr,uid,args, offset=offset, limit=limit, order=order,context=context, count=count)
        return res
    
class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    def init(self,cr):
        #UPDATE DATABASE TO AVOID NULL PROBLEMS
        query="""UPDATE sale_order_line SET name = '.' WHERE name IS NULL"""
        cr.execute(query)
    
    def compute_stock(self):
        self._qty_virtual_stock()
        self._qty_real_stock()
    
    def _qty_virtual_stock(self):
        for sol in self:
            if sol.product_id:
                sol.virtual_stock = sol.product_id.with_context(location=sol.order_id.warehouse_id.lot_stock_id.id).virtual_available
            else:
                sol.virtual_stock = 0 
    
    def _qty_real_stock(self):
        for sol in self:
            if sol.product_id:
                sol.real_stock = sol.product_id.with_context(location=sol.order_id.warehouse_id.lot_stock_id.id).qty_available
            else:
                sol.real_stock = 0
                
    
    @api.multi
    def write(self, vals):
        res = super(sale_order_line,self).write(vals)
        for line in self:
            line.set_brut_price()
        return res
    
    @api.model
    @api.returns('self', lambda value:value.id)
    def create(self, vals):
        res = super(sale_order_line,self).create(vals)
        res.set_brut_price()
        return res
    
    @api.one
    def set_brut_price(self):
        if self._context.get('set_brut_price',False):
            return
        if self.order_id and self.order_id.state == 'draft':
            if self.product_id:
                self.with_context(set_brut_price=True).brut_sale_price = self.product_id.list_price
            else:
                self.with_context(set_brut_price=True).brut_sale_price = 0
    
    
    @api.multi
    def copy(self, default=None):
        if not default:
            default = {}
        default['purchase_line_ids'] = None
        return super(sale_order_line, self).copy(default)
    
    @api.multi
    def product_id_change(self, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False):
        
        # We change the default behaviour : 
        #     Product sale description is not appended to sale_order_line.name
        #     but to sale_order_line_notes
        
        updated= False
        if not flag and product:
            name = self.env['product.product'].browse(product).name_get()[0][1]
            flag = True
            updated=True
        
        res = super(sale_order_line,self).product_id_change(pricelist=pricelist, product=product, qty=qty,
            uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag)
        
        product = self.env['product.product'].browse(product)
        
        if product:
            res['value']['notes'] = product.description_sale
        
        if updated:
            res['value']['name'] = name
          
        
        return res

    @api.multi    
    def product_id_change_with_wh_quotation_address(self, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, warehouse_id=False, quotation_address_id=False):
        
        res = super(sale_order_line, self).product_id_change_with_wh_quotation_address(pricelist, product, qty=qty,
            uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, warehouse_id=warehouse_id, quotation_address_id=quotation_address_id)
        
        if res and res.get('warning',False) and res['warning'].get('title',False) and res['warning']['title'] == _('Configuration Error!'):
            del res['warning'] 
            
        
        old_price = self._context.get('price_unit',0)
        new_price = res.get('value',{'price_unit':0}).get('price_unit',0)
        
        ''' NO WARNING NEEDED ANYMORE
        if old_price and old_price != new_price:
            res['warning'] = {'title':'Unit price changed','message':_('Unit price has been changed from %s to %s.')%(old_price,new_price)}
        '''
        
        
        #compute qty real/virtual stock    
        product_obj = self.env['product.product'].browse(product)
        warehouse = self.env['stock.warehouse'].browse(warehouse_id)
        if not res:
            res = {}
        if not 'value' in res:
            res['value'] = {}
        
        res['value']['virtual_stock'] = product_obj.with_context(location=warehouse.lot_stock_id.id).virtual_available
        res['value']['real_stock'] = product_obj.with_context(location=warehouse.lot_stock_id.id).qty_available
        res['value']['brut_sale_price'] = product_obj.list_price
        
        return res
    
        
    virtual_stock = fields.Float('Virtual stock', compute=_qty_virtual_stock)
    real_stock = fields.Float('Real stock', compute=_qty_real_stock)
    brut_sale_price = fields.Float(string="Brut sale price", readonly=True)

    purchase_line_ids = fields.Many2many('purchase.order.line', 'purchase_line_sale_line_rel', 'sale_line_id', 'purchase_line_id', 'Purchase lines')
    procurement_ids=fields.One2many(auto_join=True)
    product_code = fields.Char('Product', related='product_id.default_code')
    
    notes = fields.Text(string='Notes',help='This is automatically filled by the product sale description if it is not blank.')

sale_order_line()   

    
class sale_order(models.Model):
    _inherit = 'sale.order'
    
    _order = 'id desc'
    
    @api.returns('self')
    def search(self, cr, user, args, offset=0, limit=None, order=None, context=None, count=False):
        #if my_dpt : display picking of sale teams of current user. If user is not linked to a sale team, display all picks
        section_ids = self.pool.get('crm.case.section').search(cr, user, [('member_ids','in',user)], context=context)
        if context.get('my_dpt',False) and section_ids:
            args.append(('section_id','in',section_ids)) 
        res = super(sale_order, self).search(cr, user, args, offset=offset, limit=limit, order=order, context=context, count=count)
        return res
    

    @api.multi
    def action_cancel(self):
        res = super(sale_order, self).action_cancel()
        for sale in self:
            for pick in sale.picking_ids:
                pick.action_cancel()
        return res
    
    def action_cancel_draft(self, cr, uid, ids, *args):
        if not len(ids):
            return False
        cr.execute('select id from sale_order_line where order_id IN %s and state=%s', (tuple(ids), 'cancel'))
        line_ids = map(lambda x: x[0], cr.fetchall())
        self.write(cr, uid, ids, {'state': 'draft', 'invoice_ids': [], 'shipped': 0})
        self.pool.get('sale.order.line').write(cr, uid, line_ids, {'procurement_path':False, 'procurement_path_backup':False,'invoiced': False, 'state': 'draft', 'invoice_lines': [(6, 0, [])]})
        for inv_id in ids:
            # Deleting the existing instance of workflow for PO
            self.delete_workflow(cr, uid, [inv_id]) # TODO is it necessary to interleave the calls?
            self.create_workflow(cr, uid, [inv_id])
        for (id,name) in self.name_get(cr, uid, ids):
            message = _("The sales order '%s' has been set in draft state.") %(name,)
            self.log(cr, uid, id, message)
        return True
    
    #own template to send by email
    @api.multi
    def action_quotation_send(self):
        action_dict = super(sale_order, self).action_quotation_send()
        try:
            if self.state in ('draft','sent'):
                template_id = self.env['ir.model.data'].get_object_reference('elneo_sale', 'email_template_quotation')[1]
            else:
                template_id = self.env['ir.model.data'].get_object_reference('elneo_sale', 'email_template_sale_confirmation')[1]
            ctx = action_dict['context']
            ctx['default_template_id'] = template_id
            ctx['default_use_template'] = True
        except Exception:
            pass
        return action_dict
    
    
    
    @api.multi 
    def action_button_confirm_jit(self):
        self.jit = True
        return self.action_button_confirm()
    
    @api.multi 
    def action_button_confirm_no_jit(self):
        self.jit = False
        return self.action_button_confirm()
    
    
    #Override order confirmation to check 'stat on invoice date' if a product is in a category checked as 'stat on invoice date default'
    @api.multi 
    def action_button_confirm(self):
        #recursive function to check if product categories are stat_on_invoice_date by default
        def is_stat_on_invoice_date(product):
            categ = product.categ_id
            while categ:
                if categ.stat_on_invoice_date_default:
                    return True
                categ = categ.parent_id
            
        result = super(sale_order,self).action_button_confirm() 
        #check sale order stat_on_invoice_date if needed
        for sale in self:
            for line in sale.order_line:
                if line.product_id:
                    #save brut_sale_price
                    line.brut_sale_price = line.product_id.product_tmpl_id.list_price
                    
                    if is_stat_on_invoice_date(line.product_id):
                        sale.stat_on_invoice_date = True
                        break;
        return result
    
    
    @api.multi
    def print_quotation(self):
        assert len(self) == 1, 'This option should only be used for a single id at a time'
        self.signal_workflow('quotation_sent')
        if self.state in ('draft','sent'):
            return self.env['report'].get_action(self,'sale.report_saleorder')
        else:
            return self.env['report'].get_action(self,'elneo_report.report_saleorder_confirmation_template')
    
    @api.multi
    def onchange_pricelist_id(self, pricelist_id, order_lines):
        res = super(sale_order, self).onchange_pricelist_id(pricelist_id, order_lines)
        if res and 'warning' in res:
            del res['warning']
        return res

    @api.one
    @api.depends('invoice_ids.state','force_is_invoiced')
    def _get_is_invoiced(self):
        result = {}  
        
        self.is_invoiced = False
        
        # if is force_is_invoice
        if self.force_is_invoiced:
            self.is_invoiced = True
            
        # Maintenance Order
        # V8 : TO PUT IN A SEPARATE MODULE#
        #if order.intervention_id and (len(order.invoice_ids) > 0):
        #    is_invoiced = True
    
        
        if not self.is_invoiced:
            has_invoice_line = False
            has_order_line = False
            all_order_line_is_invoiced = True
            for order_line in self.order_line:
                if order_line.state == 'cancel':
                    continue
                
                has_order_line = True
                quantityInInvoiceLine = 0
                for invoice_line in order_line.invoice_lines:
                    if invoice_line.invoice_id.state != "draft" and invoice_line.invoice_id.state != "cancel" and invoice_line.invoice_id.type == "out_invoice":
                        has_invoice_line = True
                        quantityInInvoiceLine += invoice_line.quantity
                if quantityInInvoiceLine != order_line.product_uom_qty:
                    all_order_line_is_invoiced = False
                    break
            self.is_invoiced = all_order_line_is_invoiced and has_invoice_line and has_order_line

        # if linked invoice
        if not self.is_invoiced:
            invoiceAmounts = {}
            saleAmounts = {}
            for invoice in self.invoice_ids:
                if invoice.state != "draft" and invoice.state != "cancel" and invoice.type == "out_invoice":
                    if not invoice.id in invoiceAmounts:
                        invoiceAmounts[invoice.id] = invoice.amount_total
                        for sale in invoice.sale_order_ids:
                            if not sale.id in saleAmounts:
                                saleAmounts[sale.id] = sale.amount_total
                           
            sumInvoice = 0
            sumSale = 0
            for key in invoiceAmounts.keys():
                sumInvoice += invoiceAmounts[key]
                
            for key in saleAmounts.keys():
                sumSale += saleAmounts[key]

            if (sumInvoice != 0 or sumSale != 0) and sumInvoice >= sumSale:
                self.is_invoiced = True
                
    @api.one
    @api.depends('order_line.margin','amount_untaxed')        
    def _sale_margin(self):
        self.sale_margin = 1.0
        margin_amount = 0.0
        for line in self.order_line:
            margin_amount += line.margin or 0.0
        
        if (self.amount_untaxed - margin_amount) != 0.0:
            self.sale_margin = (self.amount_untaxed / (self.amount_untaxed - margin_amount))
        
                
    #function return all pickings visible in sale order
    @api.multi
    def _get_out_picking_ids(self):
        for sale in self:
            if not sale.procurement_group_id:
                continue
            sale.out_picking_ids = self.env['stock.picking'].search([('group_id', '=', sale.procurement_group_id.id),('picking_type_id.code','!=','incoming')])
    
    
    jit = fields.Boolean('Just in time ?')
    partner_name = fields.Char('Customer name', related="partner_id.name")
    sale_margin = fields.Float(compute='_sale_margin', string='Marge Coefficient', store=True, help="it gives a ratio representing the margin.")
    out_picking_ids = fields.One2many(compute='_get_out_picking_ids', comodel_name='stock.picking', method=True, string='Picking associated to this sale')  
    margin = fields.Float(track_visibility='always')
    partner_order_id = fields.Many2one('res.partner', 'Order Address', readonly=True, required=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},default=lambda rec: rec.partner_id, help="Order address for current sales order.")
    carrier_id = fields.Many2one('delivery.carrier', 'Delivery Method', help="Complete this field if you plan to invoice the shipping based on picking.")
    is_invoiced = fields.Boolean(compute=_get_is_invoiced, string="Is invoiced", readonly=True,help="Checked if the sale order is completely invoiced",store=True)
    force_is_invoiced = fields.Boolean("Force is invoiced",help="Force the 'invoiced' state for this sale order")
    order_policy = fields.Selection([
                ('manual', 'On Demand'),
                ('picking', 'On Delivery Order'),
                ('prepaid', 'Before Delivery'),
            ],string='Create Invoice', required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
            help="""On demand: A draft invoice can be created from the sales order when needed. \nOn delivery order: A draft invoice can be created from the delivery order when the products have been delivered. \nBefore delivery: A draft invoice is created from the sales order and must be paid before the products can be delivered.""")
    
    stat_on_invoice_date = fields.Boolean("Stats on invoice date")
    
    section_id = fields.Many2one(required=True)
    invoice_ids = fields.Many2many(readonly=False)
    order_line=fields.One2many(auto_join=True)
    procurement_group_id = fields.Many2one(index=True)
    
    @api.multi
    def copy(self, default=None):
        if not default:
            default = {}
        return super(sale_order, self.with_context(copy=True)).copy(default) 
    
    @api.one
    def write(self,values):
    
        #Make sure that address changing is allowed
        # Invoice Address
        if(values.has_key('partner_invoice_id')):
            for invoice in self.invoice_ids:
                if invoice.state!='draft':
                    raise Warning(_("Can't change address"),_("You cannot change the invoice address as there is an invoice which is not draft at most!"))
            
            for invoice in self.invoice_ids:
                self.invoice_ids.partner_id = values['partner_invoice_id']
        
        # Shipping Address
        if(values.has_key('partner_shipping_id')):
            if self.picking_ids.filtered(lambda r:r.picking_type_id.code=='outgoing' and r.state == 'done'):
                raise Warning(_("Can't change address"),_("You cannot change the shipping address as there is a shipment which is done at most!"))
                
            pickings = self.picking_ids.filtered(lambda r:r.picking_type_id.code=='outgoing' and r.state != 'done')
            for pick in pickings: 
                pick.partner_id=values['partner_shipping_id']
        
        return super(sale_order,self).write(values)
    
    @api.constrains('carrier_id','shop_sale')
    @api.one
    def _check_carrier_id(self):
        from_opportunity = False
        if self._context and self._context.get('active_model',False) and self._context['active_model'] == 'crm.lead':
            from_opportunity = True
        if self._context.get('copy',False):
            return
        
        if not self.shop_sale and not self.carrier_id and (not from_opportunity) and \
            (not self.outgoing_picking_type or (self.outgoing_picking_type.need_carrier and not self.carrier_id)):
            raise ValidationError("A delivery method has to be chosen")
    
    
    #function to rewrite when odoo core will be migrated to new api
    def onchange_warehouse_id(self, cr, uid, ids, warehouse_id, context=None):
        res = super(sale_order, self).onchange_warehouse_id(cr, uid, ids, warehouse_id, context)
        self.browse(cr, uid, ids, context).order_line.compute_stock()
        return res
    
    @api.onchange('order_line')
    def onchange_order_lines(self):
        self.order_line.compute_stock()
        
    @api.multi
    def onchange_partner_id(self, partner):
        res = super(sale_order, self).onchange_partner_id(partner)
        if partner:
            partner_obj = self.env['res.partner'].browse(partner)
            if not res:
                res = {}
            if not 'value' in res:
                res['value'] = {}
            res['value']['partner_order_id'] = partner_obj.address_get(['default'])['default']
            res['value']['sale_note'] = super(sale_order,self).get_salenote(partner)
        return res

    ''' uncomment if we want to select customer from contact
        @api.onchange('partner_order_id')
        def onchange_partner_order_id(self):
            if not self.partner_order_id:
                self.partner_id = False
                self.partner_invoice_id = False
                self.partner_shipping_id = False
                self.quotation_address_id = False
                self.payment_term = False
                self.fiscal_position = False
            else:
                # GET the commercial entity
                if self.partner_order_id.commercial_partner_id:
                    self.partner_id = self.partner_order_id.commercial_partner_id
                    addr = self.partner_id.address_get(['delivery', 'invoice', 'contact'])
                    self.partner_shipping_id = addr['delivery']
                    self.partner_invoice_id = addr['invoice']
    '''
                
    @api.onchange('quotation_address_id')
    def onchange_quotation_address_id(self):
        
        if not self.quotation_address_id:
            self.partner_id = False
            self.partner_invoice_id = False
            self.partner_shipping_id = False
            self.partner_order_id = False
            self.payment_term = False
            self.fiscal_position = False
        else:
            # GET the commercial entity
            if self.quotation_address_id.commercial_partner_id:
                self.partner_id = self.quotation_address_id.commercial_partner_id
                addr = self.partner_id.address_get(['delivery', 'invoice', 'contact'])
                self.partner_shipping_id = addr['delivery']
                self.partner_invoice_id = addr['invoice']


class pricelist_partnerinfo(models.Model):
    _inherit = 'pricelist.partnerinfo'
    
    brut_price = fields.Float('Brut price')
    discount = fields.Float('Discount')
    
    @api.one
    @api.onchange('brut_price')
    def onchange_brut_price(self):
        if self.discount and self.brut_price:
            self.price = self.brut_price - (self.brut_price * (self.discount/100))
        else:
            self.price = self.brut_price
    
    @api.one
    @api.onchange('discount')
    def onchange_discount(self):
        if self.discount and self.brut_price:
            self.price = self.brut_price - (self.brut_price * (self.discount/100))
        else:
            self.price = self.brut_price
    
    @api.one        
    @api.onchange('price')
    def onchange_price(self):
        if self.price and self.brut_price:
            self.brut_price = (100*self.price)/(100-self.discount)
        else:
            self.brut_price = self.brut_price
            


class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    sale_order_ids =fields.Many2many('sale.order', 'sale_order_invoice_rel', 'invoice_id', 'order_id', string='Sale orders')

