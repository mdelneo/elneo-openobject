from openerp import  models,fields, api

class res_config(models.TransientModel):
    _inherit = 'maintenance.config.settings'

    default_cpi_type = fields.Many2one('cpi.be.type','Default Maintenance CPI type',help="The default cpi type")

    @api.multi
    def set_default_cpi_type(self):
        self.env['ir.config_parameter'].set_param('elneo_maintenance_project_invoicing.default_cpi_type',repr(self.default_cpi_type.id))
        
    @api.model
    def get_default_cpi_type(self,fields):
        default_cpi_type = self.env['ir.config_parameter'].get_param('elneo_maintenance_project_invoicing.default_cpi_type',False)
        
        if default_cpi_type != 'False':
            default_cpi_type = int(default_cpi_type)
        else:
            default_cpi_type = False
        return {'default_cpi_type':default_cpi_type,}