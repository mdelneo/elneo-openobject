from openerp import models,fields,api, _, workflow
from datetime import datetime, timedelta
from openerp import exceptions

class hr_employee(models.Model):
    _name = 'hr.employee'
    _inherit = 'hr.employee'


    #Display days remaining in all leaves types for employee when he do an holiday request
    @api.multi
    def _get_days(self, field_names, args):
        self._cr.execute("select employee_id,type,holiday_status_id, sum(number_of_days) from hr_holidays left join hr_holidays_status on hr_holidays_status.id = holiday_status_id  where hr_holidays_status.count and  state = 'validate' and employee_id in %s group by employee_id, type,holiday_status_id order by employee_id,holiday_status_id,type;",(tuple(self._ids),))
        req_res = self._cr.fetchall()
        res = {}
        for employee in self:
            res[employee.id] = {'days_remaining':0, 'days_total':0}
        
        for (employee_id, holiday_type, holiday_status_id, days) in req_res:
            if not employee_id in res:
                res[employee_id] = {}
                res[employee_id] = {'days_remaining':0, 'total':0}
            if holiday_type != 'remove':
                res[employee_id]['days_total'] = res[employee_id]['days_total']+days
            
            res[employee_id]['days_remaining'] = res[employee_id]['days_remaining']+days
        
        for employee in self:
            employee.days_remaining = res[employee.id]['days_remaining']
            employee.days_total = res[employee.id]['days_total'] 
            
    
    national_id =  fields.Char('National ID', size=32)
    id_id =  fields.Char('Identity card number', size=32)
    worker_id =  fields.Char('Worker number', size=32)
    contract_type =  fields.Selection([('employee','Employee'),('worker','Laborer'),('interim','Interim'),('independant','Self employed'),('student','Student')],'Contract type')
    start_date =  fields.Date('Begin date')
    test_period_end =  fields.Date('End of trial period')
    section =  fields.Many2one('crm.case.section', related='user_id.default_section_id', string='Department', readonly=True)
    days_remaining = fields.Float(compute='_get_days', string="Days remaining", readonly=True)
    days_total = fields.Float(compute='_get_days', string="Days total", readonly=True)
    
hr_employee()