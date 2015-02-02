from openerp import models,fields

class user_dept_zip(models.Model):
    _name = 'res.user.zip.rel'
    
    user = fields.Many2one('res.users', string='Seller', required=True)
    zip_min = fields.Char('Zip min', size=24, required=True)
    zip_max = fields.Char('Zip max', size=24, required=True)
    department = fields.Many2one('crm.case.section',string='Sales Team', required=True)

user_dept_zip()

class partner_sale_exception(models.Model):
    _name = 'res.partner.sale.exception'
    
    user = fields.Many2one('res.users','User',required=True)
    department = fields.Many2one('crm.case.section','Sales Team',required=True)
    partner = fields.Many2one('res.partner','Partner',required=True)
    

partner_sale_exception()