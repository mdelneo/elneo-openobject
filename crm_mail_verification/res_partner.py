from openerp import models, api
from openerp.exceptions import ValidationError
import re

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    REGEX="\\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,10}\\b"
    
    @api.one
    @api.constrains('email')
    def _check_email(self):
        try:
            email = str(self.email)
        except:
            raise ValidationError('Email is not well written : '+self.email)
        
        if not re.search(self.REGEX, email.upper()):
            raise ValidationError('Email is not well written : '+email)