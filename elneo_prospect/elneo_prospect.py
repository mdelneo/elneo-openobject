from openerp import models,fields

class res_partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    prospect = fields.Boolean('Prospect')
    
res_partner()