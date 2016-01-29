from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
from openerp import models,fields,api
from operator import itemgetter
import re

class sale_quotation_text_element(models.Model):
    _name = 'sale_quotation.text.element'
    _description = "Quotation elements are appendix to add inside a quotation"
    _rec_name = 'code'
    
    @api.model
    def _lang_get(self):
        obj = self.env['res.lang']
        res = obj.search([])
        return [(r.code, r.name) for r in res] + [('','')]
    
    code = fields.Char('Code', size=255, required=True, help="Code for Quotation Elements")
    content = fields.Text('Content', help="Content for Quotation Elements")
    default_position = fields.Selection([('before', 'Before'), ('after', 'After'), ('final', 'Final')], 'Default position', default='before')
    default_page_break_before = fields.Boolean('Page break before', help="Check if you want a page break after quotation element by default") 
    default_page_break_after = fields.Boolean('Page break after', help="Check if you want a page break before quotation element by default")
    default_sequence = fields.Integer('Sequence', help="Gives the sequence order of displayed text elements in the report.") 
    default_displayed = fields.Boolean('Displayed')
    lang = fields.Selection(_lang_get, 'Language', size=32)
    
    
sale_quotation_text_element()

class sale_quotation_order_text_element(models.Model):
    _name = 'sale_quotation.order.text.element'
    _description = "Quotation text elements included in a sale order."
    _order = 'sequence'
    
    '''
    @api.onchange('text_element_id')
    def onchange_text_element(self):    
        return    
        if self.text_element_id:
            sale_quotation_text_element = self.text_element_id
            self.content = sale_quotation_text_element.content
            self.position = sale_quotation_text_element.default_position
            self.page_break_before = sale_quotation_text_element.default_page_break_before
            self.page_break_after = sale_quotation_text_element.default_page_break_after
            self.text_element_name = sale_quotation_text_element.code '''
    
    @api.multi
    def _text_element_name(self):
        for element in self:
            if element.text_element_id:
                element.text_element_name = element.text_element_id.code
            else: 
                element.text_element_name = ''
            
    
    '''This function replace text between [] by it's value''' 
    @api.one    
    def _get_content_interpreted(self):
        if self.content:
            fields = re.findall("\[([^\]]*)\]*",self.content)
            content_interpreted = self.content
            for field in fields:
                sub_fields = field.split('.')
                value = self.sale_order_id
                for sub_field in sub_fields:
                    try:
                        #test if field is date
                        value = datetime.strptime(value[sub_field],'%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y')
                    except:
                        value = value[sub_field]
                if not value:
                    value = ''
                content_interpreted = content_interpreted.replace('['+field+']',value)
            self.content_interpreted = content_interpreted
        
    @api.one
    def show(self):
        self.displayed = True
    
    @api.one    
    def hide(self):
        self.displayed = False
    
    displayed = fields.Boolean('Displayed')
    sale_order_id = fields.Many2one('sale.order', 'Sale order', help="Related sale order")        
    text_element_id = fields.Many2one('sale_quotation.text.element', 'Text element', help="Related text element")
    text_element_name = fields.Char(method=True, string="Text element", readonly=True, type="char", compute='_text_element_name') 
    content = fields.Text('Content', help="content copied from Quotation Elements")
    content_interpreted = fields.Text('Content interpreted', help='Content, with text between "[[]]" replaced by t-field.', compute='_get_content_interpreted') 
    position = fields.Selection([('before', 'Before'), ('after', 'After'), ('final', 'Final')], 'Position', help="Position of text element set to default position of selected Text Element.") 
    sequence = fields.Integer('Sequence', help="Gives the sequence order of displayed text elements in the report.")
    page_break_before = fields.Boolean('Page break before', help="Check if you want a page break after quotation element") 
    page_break_after = fields.Boolean('Page break after', help="Check if you want a page break before quotation element")
    
sale_quotation_order_text_element()


class sale_order(models.Model):
    _inherit = 'sale.order'
    
    '''
    @api.multi
    def set_decision_making_authority(self):
        for sale_order in self:
            if sale_order.quotation_address_id:
                self.pool.get("res.partner.address").set_decision_making_authority(cr, uid, sale_order.quotation_address_id.id, sale_order.section_id.id, sale_order.user_id.id, context)
        return True
    '''
    
    
    @api.multi
    def onchange_partner_id(self, partner):
        res = super(sale_order, self).onchange_partner_id(partner)
        if not res:
            res = {}
        if not 'value' in res:
            res['value'] = {}
        partner_obj = self.env['res.partner'].browse(partner)
        res['value']['quotation_text_elements'] = self._get_default_quotation_text_elements(partner_obj)
        return res
    
    
    def _get_default_quotation_text_elements(self, partner):
        if partner and partner.lang:
            all_elts = self.env['sale_quotation.text.element'].search([('lang','=',partner.lang)])
        else:
            all_elts = self.env['sale_quotation.text.element'].search([])
        result = []
        for elt in all_elts:
            result.append({
                'text_element_id': elt.id,
                'text_element_name':elt.code, 
                'content': elt.content, 
                'position':elt.default_position,
                'sequence': elt.default_sequence,
                'displayed': elt.default_displayed,
                'page_break_before':elt.default_page_break_before, 
                'page_break_after':elt.default_page_break_after,
            })
        
        result = sorted(result, key=itemgetter('sequence'))
        return result
    
    @api.one
    def _get_quotation_text_elements_before(self):
        self.quotation_text_elements_before = self.env['sale_quotation.order.text.element'].search([('sale_order_id','=',self.id),('position','=','before'),('displayed','=',True)])
    
    @api.one
    def _get_quotation_text_elements_after(self):
        self.quotation_text_elements_after = self.env['sale_quotation.order.text.element'].search([('sale_order_id','=',self.id),('position','=','after'),('displayed','=',True)])
        
    @api.one
    def _get_quotation_text_elements_final(self):
        self.quotation_text_elements_final = self.env['sale_quotation.order.text.element'].search([('sale_order_id','=',self.id),('position','=','final'),('displayed','=',True)])
        
    quotation_address_id = fields.Many2one('res.partner', 'Quotation Address', readonly=True, required=False, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, help="Quotation address for current sales order.")
    quotation_text_elements = fields.One2many('sale_quotation.order.text.element', 'sale_order_id', 'Quotation text elements') 
    quotation_text_elements_before = fields.One2many('sale_quotation.order.text.element', 'sale_order_id', 'Quotation text elements before', compute='_get_quotation_text_elements_before')
    quotation_text_elements_after = fields.One2many('sale_quotation.order.text.element', 'sale_order_id', 'Quotation text elements after', compute='_get_quotation_text_elements_after')
    quotation_text_elements_final = fields.One2many('sale_quotation.order.text.element', 'sale_order_id', 'Quotation text elements final', compute='_get_quotation_text_elements_final')
    display_quotation_text_elements = fields.Boolean("Display quotation text elements")
    display_delay = fields.Boolean("Display delay", default=True)
    display_discount = fields.Boolean("Display discount") 
    display_total = fields.Boolean("Display total", default=True)
    display_line_price = fields.Boolean("Display price by line", default=True)    
    display_payment_term = fields.Boolean("Display payment term", default=True)  
    display_invoice_address = fields.Boolean("Display invoice address") 
    display_shipping_address = fields.Boolean("Display shipping address")
    display_descriptions = fields.Boolean("Display descriptions", default=True)
    delay_in_week = fields.Boolean("Delay in week")
    is_quotation = fields.Boolean("Is Quotation")
    quotation_validity = fields.Char('Quotation validity')
    
sale_order()


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, shop_id=0, context={}):
        
        res = super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty=qty,
            uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, context=context)
        
        if not flag:
            if not res['value']:
                res['value'] = {}
            product_obj = self.pool.get("product.product").browse(cr, uid, product, context)
            context_partner = {'lang': lang, 'partner_id': partner_id}
            res['value']['name'] = self.pool.get('product.product').name_get(cr, uid, [product_obj.id], context=context_partner)[0][1]
        
        return res
    
sale_order_line()