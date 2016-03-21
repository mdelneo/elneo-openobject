# -*- coding: utf-8 -*-
##############################################################################
#
#    Elneo
#    Copyright (C) 2011-2016 Elneo (Technofluid SA) (<http://www.elneo.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp import models, fields, api
from operator import itemgetter

import logging

class TextElement(models.Model):
    _name = 'maintenance_project_offer.text_element'
    
    @api.model
    def _lang_get(self):
        obj = self.env['res.lang']
        res = obj.search([])
        return [(r.code, r.name) for r in res] + [('','')]    
    
    code = fields.Char('Code', size=255, required=True, help="Code for Text Elements")
    content = fields.Text('Content', help="Content for Text Elements")
    default_position = fields.Selection([('before', 'Before'), ('after', 'After'), ('final', 'Final')], 'Default position', default='before')
    default_page_break_before = fields.Boolean('Page break before', help="Check if you want a page break after quotation element by default") 
    default_page_break_after = fields.Boolean('Page break after', help="Check if you want a page break before quotation element by default")
    default_sequence = fields.Integer('Sequence', help="Gives the sequence order of displayed text elements in the report.") 
    default_displayed = fields.Boolean('Displayed')
    editable = fields.Boolean('Editable')
    lang = fields.Selection(_lang_get, 'Language', size=32)
    order_text_element_id = fields.One2many('maintenance_project_offer.order_text_element', 'text_element_id')
    
class OrderTextElement(models.Model):
    _name = 'maintenance_project_offer.order_text_element'
    
    @api.multi
    def _text_element_name(self):
        for element in self:
            if element.text_element_id:
                element.text_element_name = element.text_element_id.code
            else:
                element.text_element_name = 'Empty name'
    
    def _get_content_interpreted(self):
        return self.content
    
    @api.one
    def show(self):
        self.displayed = True
    
    @api.one
    def hide(self):
        self.displayed = False
        
    displayed = fields.Boolean('Displayed')
    project_id = fields.Many2one('maintenance.project', 'Project Offer', help="Related installation")        
    text_element_id = fields.Many2one('maintenance_project_offer.text_element', 'Text element', help="Related text element")
    text_element_name = fields.Char(string="Text element", readonly=True, type="char", compute='_text_element_name') 
    content = fields.Text('Content', help="content copied from Quotation Elements")
    content_interpreted = fields.Text('Content interpreted', help='Content, with text between "[[]]" replaced by t-field.', compute='_get_content_interpreted') 
    position = fields.Selection([('before', 'Before'), ('after', 'After'), ('final', 'Final')], 'Position', help="Position of text element set to default position of selected Text Element.") 
    sequence = fields.Integer('Sequence', help="Gives the sequence order of displayed text elements in the report.")
    page_break_before = fields.Boolean('Page break before', help="Check if you want a page break after quotation element") 
    page_break_after = fields.Boolean('Page break after', help="Check if you want a page break before quotation element")
    
class MaintenanceProject(models.Model):
    _inherit = 'maintenance.project'
    
    @api.onchange('installation_id')
    def _onchange_installation_id(self):
        self.text_elements = self.env['maintenance_project_offer.order_text_element']
        for element in self._get_default_text_elements():
            self.text_elements |= self.text_elements.new(element)
        
    
    def _get_default_text_elements(self):
        partner = self.installation_id.partner_id
        
        if partner and partner.lang:
            elements = self.env['maintenance_project_offer.text_element'].search([('lang', '=', partner.lang)])
        else:
            elements = self.env['maintenance_project_offer.text_element'].search([])
            
        result = []
        for item in elements:
            
            result.append({
                'text_element_id': item.id,
                'text_element_name': item.code,
                'content': item.content,
                'position': item.default_position,
                'sequence': item.default_sequence,
                'displayed': item.default_displayed,
                'page_break_before': item.default_page_break_before,
                'page_break_after': item.default_page_break_after
            })
            
        result = sorted(result, key=itemgetter('sequence'))
        
        return result
    
    '''
    @api.one
    def _get_text_elements(self): # axe if useful (checks install > partner > lang)
      #  if self.installation_id and self.installation:
      #      installation = self.installation
      #      if installation.partner_id and installation.partner:
      #          partner = installation.partner
        if self.installation_id.partner_id.lang:
            text_elements = self.env['maintenance_project_offer.text_element'].search([('lang', '=', self.installation_id.partner_id.lang)])
        else:
            text_elements = self.env['maintenance_project_offer.text_element'].search([])
        
        
        order_stuff = []
        for text_element in text_elements:
            order = self.env['maintenance_project_offer.order_text_element'].search([('text_element_id','=',text_element.id),('project_id','=',self.id)])
            if order:
                order.displayed = text_element.default_displayed
                order.position  = text_element.default_position
                order.sequence  = text_element.default_sequence
                order.page_break_before = text_element.default_page_break_before 
                order.page_break_after  = text_element.default_page_break_after
                order_stuff.append(order)
            else :
                order_stuff.append(text_element)
            
        self.text_elements = order_stuff
        
#        self.text_elements = self.env['text_element'].search([])
    '''

    @api.one
    def _get_text_elements_before(self):
        self.text_elements_before = self.env['order_text_element'].search([('project_id','=',self.id),('position', '=', 'before'),('displayed','=',True)])
    
    @api.one        
    def _get_text_elements_after(self):
        self.text_elements_after  = self.env['order_text_element'].search([('project_id','=',self.id),('position', '=', 'after'), ('displayed','=',True)])
        
    @api.one            
    def _get_text_elements_final(self):
        self.text_elements_final  = self.env['order_text_element'].search([('project_id','=',self.id),('position', '=', 'final'), ('displayed','=',True)])

    text_elements        = fields.One2many('maintenance_project_offer.order_text_element', 'project_id', 'Text elements')#, compute='_get_default_text_elements')
    text_elements_before = fields.One2many('maintenance_project_offer.order_text_element', 'project_id', 'Text elements before', compute='_get_text_elements_before')
    text_elements_after  = fields.One2many('maintenance_project_offer.order_text_element', 'project_id', 'Text elements after',  compute='_get_text_elements_after')
    text_elements_final  = fields.One2many('maintenance_project_offer.order_text_element', 'project_id', 'Text elements final',  compute='_get_text_elements_final')
    
     