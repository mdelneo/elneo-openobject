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
        timeofuse_pool = self.pool.get("maintenance.intervention.timeofuse")
        
        
        
        timeofuses = self.env['maintenance.intervention.timeofuse'].search([('intervention_id','=',self.env.context.get('active_id',False)),('time_of_use','=',None)])
        timeofuses.unlink()
        
        res = self.env['maintenance.intervention'].browse(self.env.context.get('active_ids',False)).with_context(intervention_force_done=True).action_done()
        return {'type': 'ir.actions.act_window_close'}
