
from openerp import models, fields, api


class EDIImportWizard(models.TransientModel):
    _name = 'edi.import.wizard'
    
    all = fields.Boolean(string='Every processor',help='Launch import on every processor',default=True)
    
    @api.multi
    def run(self):
    
        for processor in self.env['edi.processor'].search([('active','=',True)]):
            processor.import_messages()
                                                        
        
class EDIProcessWizard(models.TransientModel):
    _name = 'edi.process.wizard'
    
    all = fields.Boolean(string='Every processor',help='Launch process on every processor',default=True)
    
    @api.multi
    def run(self):
    
        for processor in self.env['edi.processor'].search([('active','=',True)]):
            processor.process_messages()