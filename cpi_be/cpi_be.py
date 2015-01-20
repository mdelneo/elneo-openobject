#from osv import osv, fields
from datetime import datetime, timedelta

from openerp import models, fields, api, _

class cpi_be_type(models.Model):
    _name = 'cpi.be.type'
    
    name = fields.Char("Name", size=255)
    description = fields.Char("Description", size=1024)
    entries = fields.One2many('cpi.be.entry','type_id', string='Entries')
    
    '''
    _columns = {
        'name':fields.char("Name", size=255),
        'description':fields.char("Description", size=1024),  
        'entries':fields.one2many('cpi.be.entry','type_id', string='Entries')
    }
    '''
cpi_be_type()


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
    
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if not args:
            args = []
        
        ids = []
        req_ids = []
        if name:
            self.cr.execute("select id from cpi_be_entry where to_char(month,'09')||'/'||year like %s",('%'+name+'%',))
            req_ids = map(lambda x: x[0], self.cr.fetchall())
        
        if name:
            ids = self.search([('id', 'in', req_ids)]+args, limit=limit)
        else:
            ids = self.search(args, limit=limit)
        
        
        return self.name_get(ids,)
    
    '''
    _columns = {
        'type_id':fields.many2one('cpi.be.type', string="Type"),
        'year':fields.integer("Year"), 
        'month':fields.integer("Month"), 
        'value':fields.float("Value")
    }
    '''
    def _check_date(self, cr, uid, ids):
        for cpi in self.browse(cr, uid, ids):
            if cpi.month < 1 or cpi.month > 12:
                return False 
        return True
    
    _constraints = [(_check_date, 'Error: invalid month', ['month']), ]
    
    _sql_constraints = [
        ('cpi_be_entry_unique', 'unique(type_id,year,month)', 'For the same type, year and month must be unique')
    ]
    
     
    
cpi_be_entry()

class cpi_be_update_wizard(models.TransientModel):
    _name = 'cpi.be.update.wizard'
    
    @api.multi
    def action_update(self):
        self.env["scheduler.cpi_be"].import_cpi_be_all()
        return {'type': 'ir.actions.act_window_close'}
    
cpi_be_update_wizard()
