'''
Created on 24 sept. 2013

@author: technofluid
'''
from openerp import models, api

class maintenance_timeofuse_intervention_confirm_wizard(models.TransientModel):
    _name = 'maintenance.timeofuse.intervention.confirm.wizard'
    
    _rec_name='id'
    
    @api.multi
    def confirm(self):
        self.ensure_one()
        id = self.env.context.get('active_id',False)
        for timeofuse in self.env['maintenance.intervention.timeofuse'].search([('intervention_id','=',id),('time_of_use','=',None)]):
            timeofuse.unlink()
            
        return self.env['maintenance.intervention'].browse(id).with_context(intervention_force_done=True).action_done()