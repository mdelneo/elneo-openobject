from openerp import models, api, fields


class procurement_run_wizard(models.TransientModel):
    _name = 'procurement.run.wizard'

    @api.multi
    def run_procurements(self):
        self.env['procurement.order'].run_procurements()