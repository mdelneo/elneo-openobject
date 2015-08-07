'''
Created on 28 mai 2013

@author: technofluid
'''
from osv import osv, fields

class wizard_move_element(osv.osv_memory):
    _name = 'wizard.move.element'
    
    _columns = {
        'installation_id':fields.many2one('maintenance.installation', string="New installation")
    } 
    
    def change_installation(self, cr, uid, ids, context=None):
        maintenance_element_ids = context.get("active_ids",False)
        installation_id = False
        for wiz in self.browse(cr, uid, ids, context):
            if wiz.installation_id:
                installation_id = wiz.installation_id.id
        if maintenance_element_ids and installation_id:
            self.pool.get("maintenance.element").write(cr, uid, maintenance_element_ids, {'installation_id':installation_id}, context=context)
        return {'type': 'ir.actions.act_window_close'} 
                
        
wizard_move_element()