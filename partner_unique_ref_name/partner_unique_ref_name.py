from openerp import models, api
from openerp.exceptions import ValidationError
from openerp.tools.translate import _

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    @api.one
    @api.constrains('ref','name')
    def _check_ref(self):
        if self.is_company:
            partners_with_same_ref = self.search([('ref','=',self.ref)])
            for partner in partners_with_same_ref:
                if partner.id != self.id:
                    raise ValidationError(_('Another partner exists with the same reference (%s)')%(self.ref,))
            '''partners_with_same_name = self.search([('name','=',self.name)])
            for partner in partners_with_same_name:
                if partner.id != self.id:
                    raise ValidationError(_('Another partner exists with the same name (%s)')%(self.name,))'''
