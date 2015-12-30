'''
Created on 11 juil. 2012

@author: cth
'''

from openerp import models,fields,api, _
from openerp.exceptions import Warning
from datetime import timedelta,datetime

class maintenance_intervention_task(models.Model):
    _inherit = 'maintenance.intervention.task'
    
    def _get_default_user(self, cr, uid, context={}):
        if 'installation_id' in context and context['installation_id']:
            #search in exceptions
            area_exception = self.pool.get("maintenance.technician.area.installation.exception").search(cr, uid, [('installation_id','=',context['installation_id'])], context=context)
            if area_exception:
                user_id = self.pool.get("maintenance.technician.area.installation.exception").browse(cr, uid, area_exception[0], context=context).user_id.id
                return user_id
            
            #then search by zip
            user_id = None
            installation = self.pool.get('maintenance.installation').browse(cr, uid, context['installation_id'], context)
            zip_code = None
            if installation.address_id:
                zip_code = installation.address_id.zip
            if zip_code:
                area = self.pool.get("maintenance.technician.area").search(cr, uid, [('zip_min','<=',zip_code),('zip_max','>=',zip_code)], context=context)
                if area:
                    user_id = self.pool.get("maintenance.technician.area").browse(cr, uid, area[0], context=context).user_id.id
                    return user_id
        return None

    _defaults = {
        'user_id':_get_default_user
    }
    
maintenance_intervention_task()
    
class maintenance_technician_area(models.Model):
    _name = 'maintenance.technician.area'
    
    user_id = fields.Many2one('res.users', string='Technician', required=True) 
    zip_min = fields.Char('Zip min', size=30, required=True)
    zip_max = fields.Char('Zip max', size=30, required=True)
    
    def name_get(self, cr, user, ids, context=None):
        if not ids:
            return []
        result = []
        for area in self.browse(cr, user, ids, context=context):
            result.append((area.id, '['+area.zip_min+'-'+area.zip_max+'] '+area.user_id.name))
        return result
    
maintenance_technician_area()

class maintenance_technician_area_installation_exception(models.Model):
    _name = 'maintenance.technician.area.installation.exception'
    
    user_id = fields.Many2one('res.users', string='Technician', required=True) 
    installation_id = fields.Many2one('maintenance.installation', string='Installation', required=True)
    
maintenance_technician_area_installation_exception()
