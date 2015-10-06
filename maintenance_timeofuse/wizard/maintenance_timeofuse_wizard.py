'''
Created on 24 sept. 2013

@author: technofluid
'''
from openerp import models,fields, api

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
    
    
    
class maintenance_timeofuse_intervention_addcounter_wizard(models.TransientModel):
    _name = 'maintenance.timeofuse.intervention.addcounter.wizard'
    
    def _get_intervention(self):
        if self.env.context.get('active_id',False) and self.env.context.get('active_model') and self.env.context.get('active_model') == 'maintenance.intervention':
            return self.env.context.get('active_id',False)
    
    intervention_id=fields.Many2one('maintenance.intervention',default=_get_intervention)
    element_id = fields.Many2one('maintenance.element','Element',required=True,help='The element to link the counter')
    time_of_use= fields.Integer('Counter',required=True)
    
    @api.multi
    def add(self):
        self.ensure_one()
        
        value={'maintenance_element_id':self.element_id.id,
               'time_of_use':self.time_of_use,
               'intervention_id':self.intervention_id.id
               }
        self.env['maintenance.intervention.timeofuse'].create(value)