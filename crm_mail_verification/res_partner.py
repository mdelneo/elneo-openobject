from openerp import models, api, _
from openerp.exceptions import ValidationError
import re

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    REGEX="\\b[A-Z0-9._%+-]+@[A-Z0-9.-]+"
    
    @api.one
    @api.constrains('email')
    def _check_email(self):
        if not self.email:
            return
        try:
            email = str(self.email)
        except:
            raise ValidationError(_('Email is not well written : %s') % self.email)
        
        if not re.search(self.REGEX, email.upper()):
            raise ValidationError(_('Email is not well written : %s') % email)