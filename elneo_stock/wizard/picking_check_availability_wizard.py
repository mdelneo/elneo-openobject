from openerp import models, api, fields


class picking_check_availability_wizard(models.TransientModel):
    _name = 'picking.check.availability.wizard'

    @api.multi
    def check_availability(self):
        self.env['stock.picking'].check_availability()