#from osv import osv, fields
from datetime import datetime

from openerp import models, fields, api, _

class cpi_be_type(models.Model):
    _name = 'cpi.be.type'
    
    name = fields.Char("Name", size=255)
    description = fields.Char("Description", size=1024)
    entries = fields.One2many('cpi.be.entry','type_id', string='Entries')
 
class cpi_be_entry(models.Model):
    _name = 'cpi.be.entry'
    
    _order = 'type_id, year desc, month desc, value'
    
    type_id = fields.Many2one('cpi.be.type', string="Type")
    year = fields.Integer("Year")
    month = fields.Integer("Month") 
    value = fields.Float("Value")
    
    @api.multi
    def name_get(self):
        
        result = []
        for entry in self:
            if entry.year and entry.month:
                date = datetime.strptime(str(entry.year)+'-'+str(entry.month),'%Y-%m')
                result.append((entry.id,date.strftime('%m')+'/'+date.strftime('%Y')+' (='+str(entry.value)+')'))
            else:
                result.append((entry.id,'['+str(entry.value)+']'))
        return result
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if not args:
            args = []
        
        req_ids = []
        if name:
            self.env.cr.execute("select id from cpi_be_entry where to_char(month,'09')||'/'||year like %s",('%'+name+'%',))
            req_ids = map(lambda x: x[0], self.env.cr.fetchall())
        
        if name:
            recs = self.search([('id', 'in', req_ids)]+args, limit=limit)
        else:
            recs = self.search(args, limit=limit)
        
        
        return recs.name_get()
    
    def _check_date(self, cr, uid, ids):
        for cpi in self.browse(cr, uid, ids):
            if cpi.month < 1 or cpi.month > 12:
                return False 
        return True
    
    _constraints = [(_check_date, 'Error: invalid month', ['month']), ]
    
    _sql_constraints = [
        ('cpi_be_entry_unique', 'unique(type_id,year,month)', 'For the same type, year and month must be unique')
    ]

class cpi_be_update_wizard(models.TransientModel):
    _name = 'cpi.be.update.wizard'
    
    @api.multi
    def action_update(self):
        self.env["scheduler.cpi_be"].import_cpi_be_all()
        return {'type': 'ir.actions.act_window_close'}

