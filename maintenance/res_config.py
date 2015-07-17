from openerp import  models

class res_config(models.TransientModel):
    _name = 'maintenance.config.settings'
    _inherit = 'res.config.settings'
    
      

res_config()