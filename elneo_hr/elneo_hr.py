# -*- coding: utf-8 -*-
from openerp import models,fields,api

class HrEquipment(models.Model):
    _inherit = 'hr.equipment'
    
    purchase_date = fields.Date('Purchase date')