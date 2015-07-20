from openerp import  models,fields, api

class res_config(models.TransientModel):
    _inherit = 'maintenance.config.settings'

    timeofuse_threshold_mail = fields.Boolean('Warn on element time of use exceed?',help="Do you want to send a mail when an element time of use exceed expected time for active projects?")

    @api.multi
    def set_timeofuse_threshold_mail(self):
        
        
        self.env['ir.config_parameter'].set_param('maintenance_model.timeofuse_threshold_mail',repr(self.timeofuse_threshold_mail))
        
    
    @api.model
    def get_default_values(self,fields):
        
        timeofuse_threshold_mail = self.env['ir.config_parameter'].get_param('maintenance_model.timeofuse_threshold_mail',False)

        return {'timeofuse_threshold_mail':bool(timeofuse_threshold_mail),
                
                }