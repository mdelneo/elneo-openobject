# coding=UTF-8

import string
import math
import random


from openerp import models, fields, api


class ElneoWebshopAccount(models.Model):
    _name = 'elneo.webshop.account'
    
    partner_id = fields.Many2one('res.partner', 'Customer',ondelete='cascade') 
    login = fields.Char(size=255, string='Login',default=lambda r:r.env['ir.sequence'].get('webshop.account_number')) 
    landefeld_id = fields.Char(size=255, string='Landefeld id')
    password = fields.Char(size=255, string='Initial password') 
    email = fields.Char(size=255, string='email')
    
    @api.one
    def copy(self,default=None):
        if not default:
            default = {}
        default['login'] = self.env['ir.sequence'].get('webshop.account_number')
        return super(ElneoWebshopAccount,self).copy(default=default)

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    webshop_accounts = fields.One2many('elneo.webshop.account', 'partner_id', string='Web shop accounts')
    
    @api.model
    def get_webshop_password(self, ref):
        if not ref:
            return ''
        password = ref.lower()
        
        try:
            if len(password) >= 3:
                password = password[:3]
            
            special_chars={
                    u"à":u"a",
                    u"é":u"e",
                    u"è":u"e",
                    u"ë":u"e",
                    u"ê":u"e",
                }
     
            for k,v in special_chars.items():
                password = unicode(password).replace(unicode(k),unicode(v))
            
            for letter in password:
                if letter not in string.ascii_letters[0:26]:
                    password = password.replace(letter,'')
            
            password = password+str(int(math.floor(random.random()*10)))
        except:
            return ''
        
        return password
        
    @api.model
    def create(self,vals):
        if not 'webshop_accounts' in vals or not vals['webshop_accounts']:
            #compose account
            account = {}
            
            #set password
            if vals.has_key('name'):            
                account['password'] = self.get_webshop_password(vals['name'])
            elif (vals.has_key('firstname') and vals['firstname']) and (vals.has_key('lastname') and vals['lastname']):
                account['password'] = self.get_webshop_password(vals['firstname']+vals['lastname'])
            elif vals.has_key('firstname') and vals['firstname']:
                account['password'] = self.get_webshop_password(vals['firstname'])
            elif vals.has_key('lastname') and vals['lastname']:
                account['lastname'] = self.get_webshop_password(vals['lastname'])
            else:
                raise Warning(_('Impossible to create default webshop acccount for the contact or partner you want to create. Missing name, firstname or lastname'))
                
            
            #set login
            account['login'] = self.env['ir.sequence'].get('webshop.account_number')
            
            #set email
            mails = []
            if 'address' in vals:
                for address in vals['address']:
                    if address[0] == 0 and address[1] == 0:
                        if address[2].has_key('email'):
                            mails.append(address[2]['email'])
            for mail in mails:
                if mail and ('info@' in mail):
                    account['email'] = mail
            if not 'email' in account and mails:
                account['email'] = mails[0]
 
            vals['webshop_accounts'] = [(0, 0, account)]
        return super(ResPartner,self).create(vals)
    
    @api.one
    def copy(self, default=None):
        if default is None:
            default={}
        default['webshop_accounts'] = []
        return super(ResPartner, self).copy(default=default)
