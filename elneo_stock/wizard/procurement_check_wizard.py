from openerp import models, api, fields


class procurement_check_wizard(models.TransientModel):
    _name = 'procurement.check.wizard'

    @api.multi
    def check_procurements(self):
        self.env['procurement.order'].check_procurements()