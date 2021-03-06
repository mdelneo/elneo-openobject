from openerp import models, fields,api,_, workflow
from openerp.exceptions import Warning

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    @api.multi
    def product_id_change_with_wh(self, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, warehouse_id=False):
        res = super(sale_order_line, self).product_id_change_with_wh(pricelist, product, qty, uom, qty_uos, uos, name, partner_id, lang, update_tax, date_order, packaging, fiscal_position, flag, warehouse_id)
        if self._context.get('shop_sale',False):
            product = self.env['product.product'].browse(product)
            warehouse = self.env['stock.warehouse'].browse(warehouse_id)
            stock_real = product.with_context({'location':warehouse.lot_stock_id.id})._product_available()[product.id]['qty_available']
            if stock_real < qty:
                res['warning'] = {'title':_('Warning'),'message':_('Stock (%s) is lower than ordered quantity (%s).')%(stock_real,qty)}
        return res

class sale_order(models.Model):
    _inherit='sale.order'
    
    out_picking_ids = fields.One2many('stock.picking', compute='get_out_picking_ids')
    
    @api.multi
    def get_out_picking_ids(self):
        self.out_picking_ids = self.env['stock.picking'].search([('group_id', '=', self.procurement_group_id.id),('picking_type_id.code','=','outgoing')])
    
    def _default_shop_sale(self):
        
        user = self.env['res.users'].search([('id','=',self.env.uid),('groups_id.name','=','Warehouse / Shop seller')])
        if user:
            return True
        else:
            return False
        
    @api.multi
    def action_print_delivery_note(self):
        assert len(self) == 1, 'This option should only be used for a single id at a time'
        self.picking_ids
        return self.env['report'].get_action(self.out_picking_ids, 'stock.report_picking')
    
    @api.multi
    def action_print_confirm_invoice(self):
        assert len(self) == 1, 'This option should only be used for a single id at a time'
        if not self.invoice_ids:
            invoice_id = self.action_invoice_create()
            invoice = self.env['account.invoice'].browse(invoice_id)
        invoice = self.invoice_ids
        invoice.signal_workflow('invoice_open')
        return self.env['report'].get_action(invoice, 'l10n_be_invoice_layout.report_be_invoice')
    
    
    def shop_sale_ship(self):
        
        if self.shop_sale:
            for picking in self.picking_ids:
                for move in picking.move_lines:
                    #move.invoice_state='2binvoiced'
                    move.action_done()
                
            #if not self.invoice_ids:
            #    picking.action_invoice_create(self.warehouse_id.shop_sale_journal_id.id, False)
            
            
            #for invoice in self.invoice_ids:
                #workflow.trg_validate(self.env.uid,'account.invoice', invoice.id, 'invoice_open',self.env.cr)
            
            return True
        return False
        
    def test_shop_sale(self):
        if self.shop_sale:
            for line in self.order_line:
                if line.route_id and line.route_id.name == 'Make To Order':
                    raise Warning(_('Error !'), _("You can't sell ordered products in a shop sale."))
            return True
        return False
    
    
    def action_invoice_create(self,grouped=False, states=None, date_inv = False,):
        res = super(sale_order, self).action_invoice_create(grouped, states, date_inv)
       
        if self.shop_sale and self.warehouse_id.shop_sale_journal_id:
            invoices = self.env['account.invoice'].browse(res)
            for invoice in invoices:
                invoice.shop_sale=True
                invoice.comment = self.note
                invoice.journal_id=self.warehouse_id.shop_sale_journal_id.id
                
        return res

    shop_sale=fields.Boolean("Shop Sale (Automatic Delivery)",default=_default_shop_sale)
    
    @api.onchange('shop_sale')
    def default_invoice_policy(self):
        if self.shop_sale:
            self.order_policy = 'manual'
            self.picking_policy = 'one'
    
sale_order()

class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    # Test function to get invoice open if it is a counter sale
    def shop_sale_invoice(self):
        return False
        for sale in self.env['sale.order'].search([('invoice_ids','in',self.id),('shop_sale','=',True)]):
            if self.state == 'draft':
                return True
        
        return False