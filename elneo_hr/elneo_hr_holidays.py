from openerp import models,fields,api, _, workflow
from datetime import datetime, timedelta
from openerp.exceptions import ValidationError
from openerp.osv import osv

HR_SUPER_MANAGERS_UID = [9,10]

class hr_holidays(models.Model):
    _inherit = "hr.holidays"


    #select automatically the good type depending on remaining days
    @api.model
    def _get_default_status_id(self, requested_days):
        employees = self.env['hr.employee'].search([('user_id', '=', self._uid)])
        
        if employees:
            employee = employees[0]
        else:
            return None
        
        #check by type of holidays if user has always
        types = self.env["hr.holidays.status"].search([], order='count desc,sequence')
        
        if not types:
            return None
        
        for holiday_type in types:
            if holiday_type.count:
                leave_days = holiday_type.get_days(employee.id)[holiday_type.id]
                if leave_days['remaining_leaves'] >= requested_days and leave_days['virtual_remaining_leaves'] >= requested_days:
                    return holiday_type.id
        return types[0].id                
    
    @api.multi  
    def _get_employee(self):
        if ((self._uid == 27 or self._uid == 37) or (not self._uid)):
            return False
        else:
            employee = self.env['hr.employee'].search([('user_id','=', self._uid)])
            return employee[0].id    
    
    def onchange_type(self, cr, uid, ids, holiday_type):
        result = {}
        if holiday_type == 'employee':
            if(uid == 27 or uid == 37):
                return result
            ids_employee = self.pool.get('hr.employee').search(cr, uid, [('user_id','=', uid)])
            if ids_employee:
                result['value'] = {
                    'employee_id': ids_employee[0]
                }
        return result
        
    
    def onchange_date_from(self, cr, uid, ids, date_to, date_from, employee_id):
        try:
            result = super(hr_holidays,self).onchange_date_from(cr, uid, ids, date_to, date_from)
        except osv.except_osv:
            #by pass warning if start date > end date
            return {'value':{'number_of_days_temp': 0}}

        if date_to and date_from:
            diff_day = self._get_number_of_days_elneo(cr, uid, date_from, date_to, employee_id)
            result['value'] = {
                'number_of_days_temp': diff_day
            }
            return result
        
        result['value'] = {
            'number_of_days_temp': 0,
        }
        return result
    
    def onchange_date_to(self, cr, uid, ids, date_to, date_from, employee_id):
        try:
            result = super(hr_holidays,self).onchange_date_to(cr, uid, ids, date_to, date_from)
        except osv.except_osv:
            #by pass warning if start date > end date
            return {'value':{'number_of_days_temp': 0}}
        
        if date_to and date_from:
            diff_day = self._get_number_of_days_elneo(cr, uid, date_from, date_to, employee_id)
            result['value'] = {
                'number_of_days_temp': diff_day
            }
            return result
        result['value'] = {
            'number_of_days_temp': 0,
        }
        return result
    
    @api.onchange('number_of_days_temp')
    def onchange_number_of_days_temp(self):
        res = {}
        new_holiday_status = self._get_default_status_id(self.number_of_days_temp)
        if self.holiday_status_id and self.holiday_status_id.id != new_holiday_status:
            res = {'warning':{'title':'Warning','message':'Holiday type has changed !'}}
        self.holiday_status_id = new_holiday_status
        return res
        
    #compute number of days based on working days and leaves already encoded
    @api.model
    def _get_number_of_days_elneo(self, date_from, date_to, employee_id):
        DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
        INCREMENT=0.5
        from_date = datetime.strptime(date_from, DATETIME_FORMAT)
        to_date = datetime.strptime(date_to, DATETIME_FORMAT)
        
        
        #build array of each days of current holidays
        current_holidays = []
        current_date = from_date
        if(to_date.strftime("%H%M") > "1200"):
            to_date=to_date.replace(hour=23,minute=59)
        while current_date <= to_date:
            date_without_hours = current_date.date()
            if current_date.strftime("%H%M") > "1200":
                period = 1
            else:
                period = 0
            current_holidays.append((date_without_hours,period))
            current_date = current_date+timedelta(days=INCREMENT) 
            
        
        #find holidays already encoded and subtract days already encoded, in the current interval
        previous_holidays_objs = self.search([('state','=','validate'),('type','=','remove'),('employee_id','=',employee_id),
                '|','&',('date_from','>=',datetime.strftime(from_date, DATETIME_FORMAT)),('date_from','<=',datetime.strftime(to_date, DATETIME_FORMAT)),
                '|','&',('date_to','>=',datetime.strftime(from_date, DATETIME_FORMAT)),('date_to','<=',datetime.strftime(to_date, DATETIME_FORMAT)),
                '&',('date_from','<=',datetime.strftime(from_date, DATETIME_FORMAT)),('date_to','>=',datetime.strftime(to_date, DATETIME_FORMAT))
        ])
        
        #build dict of previous holidays
        previous_holidays = set()
        for previous_holidays_obj in previous_holidays_objs:
            current_date = datetime.strptime(previous_holidays_obj.date_from, DATETIME_FORMAT)
            date_to = datetime.strptime(previous_holidays_obj.date_to, DATETIME_FORMAT)
            if(date_to.strftime("%H%M") > "1200"):
                date_to=date_to.replace(hour=23,minute=59)
            while current_date < date_to:
                date_without_hours = current_date.date()
                if current_date.strftime("%H%M") > "1200":
                    period = 1
                else:
                    period = 0
                previous_holidays.add((date_without_hours,period))
                current_date = current_date+timedelta(days=INCREMENT)
                
        #browse array of current holidays and add one day only if date is not in previous holidays array
        number_of_days = 0
        for day_part in current_holidays:
            if ((day_part not in previous_holidays) and (day_part[0].strftime('%w') not in ['0','6'])):                
                    number_of_days = number_of_days+INCREMENT          
        
        return number_of_days
        
        ####################
        
        removed_days = set() #set of days already used by other holidays
        for previous_holiday in previous_holidays:
            current_date = from_date
            while (current_date < to_date):
                current_date_str = datetime.strftime(current_date, DATETIME_FORMAT)
                if (current_date_str >= previous_holiday.date_from) and (current_date_str <= previous_holiday.date_to) and (current_date.strftime('%w') not in ['0','6']):
                    removed_days.add(current_date)
                        
                current_date = current_date+timedelta(days=INCREMENT)
                
            if((current_date.strftime("%d%m%Y") == to_date.strftime("%d%m%Y")) & ((to_date.strftime("%H%M") > "1200") | (current_date.strftime("%H%M") > "1200"))):
                removed_days.add(current_date)
                
           
                
        days_to_remove = len(removed_days) * INCREMENT  
        
        #count days of holidays
        number_of_days = 0.0
        current_date = from_date
      
        
        while ((current_date < to_date)):
            if current_date.strftime('%w') not in ['0','6']:
                number_of_days = float(number_of_days+INCREMENT)
           
            current_date = current_date+timedelta(days=INCREMENT)
            
        if((current_date.strftime("%d%m%Y") == to_date.strftime("%d%m%Y")) & (to_date.strftime("%H%M") > "1200")):
            number_of_days = float(number_of_days+INCREMENT)
        
        return number_of_days-days_to_remove;
    
    #set manager as manager of department. Manager 2 is hard-coded  
    def set_manager(self):
        if self.department_id and self.department_id.manager_id:
            self.manager_id = self.department_id.manager_id.id
            self.manager_id2 = 27
    
    @api.onchange('department_id')
    def onchange_department(self):
        self.set_manager()
        
    #say if current user is hr manager 
    @api.model
    def uid_hr_manager(self):
        group_hr_manager_id = self.env['ir.model.data'].get_object_reference('base', 'group_hr_manager')[1]
        user = self.env['res.users'].browse(self._uid) 
        if group_hr_manager_id in [g.id for g in user.groups_id]:
            return True
        return False
           
    @api.multi
    def holidays_confirm(self):
        res = super(hr_holidays, self).holidays_confirm()
        for holiday in self:
            holiday.set_manager()
        return res
    
    #limit approval to manager or hr managers
    @api.multi
    def holidays_first_validate(self):
        res = super(hr_holidays, self).holidays_first_validate()
        for holiday in self:
            if holiday.manager_id and holiday.manager_id.user_id and holiday.manager_id.user_id.id != self._uid and not self.uid_hr_manager():
                if holiday.manager_id:
                    raise ValidationError(_('Only %s or hr managers can approve this holiday !')%holiday.manager_id.name)
                else:
                    raise ValidationError(_('Only hr managers can approve this holiday !'))
        return res
    
    #limit validation to hr manager
    @api.multi
    def holidays_validate(self):
        res = super(hr_holidays, self).holidays_validate()
        if not self.uid_hr_manager():
            raise ValidationError(_('Only hr managers can approve this holiday !'))
        return res
    
    #override _check_date function to allow overlap of 2 leaves on the same date with different types
    @api.multi 
    def _check_date(self):
        for holiday in self:
            domain = [
                ('date_from', '<=', holiday.date_to),
                ('date_to', '>=', holiday.date_from),
                ('employee_id', '=', holiday.employee_id.id),
                ('id', '!=', holiday.id),
                ('state', 'not in', ['cancel', 'refuse']),
                ('holiday_status_id','=',holiday.holiday_status_id.id), 
                ('type','=',holiday.type)
            ]
            nholidays = self.search_count(domain)
            if nholidays:
                return False
        return True
    
    #change constraint to bypass warning
    _constraints = [
        (_check_date, 'You can not have 2 leaves that overlaps on same day!', ['date_from','date_to']),
    ] 
           
    manager_user_id = fields.Many2one(related='manager_id.user_id', string='Manager user', store=True)
    manager_user_id2 = fields.Many2one(related='manager_id2.user_id', string='Manager user 2', store=True)
    
    @api.model
    def default_get(self, fields):
        res = super(hr_holidays, self).default_get(fields)
        for field in fields:
            if field == 'name':
                res['name'] = _('Holidays')
            if field == 'holiday_status_id':
                res['holiday_status_id'] = self._get_default_status_id(1)
            if field == 'date_from':
                if 'date_from' in res:
                    res['date_from'] = res['date_from'][0:10]+' 08:00:00'
                else:
                    res['date_from'] = datetime.now().strftime('%Y-%m-%d 08:00:00')
            if field == 'date_to':
                if 'date_to' in res:
                    res['date_to'] = res['date_to'][0:10]+' 16:45:00'
                else:
                    res['date_to'] = datetime.now().strftime('%Y-%m-%d 16:45:00')
            if field == 'employee_id':
                res['employee_id'] = self._get_employee()
        return res 
    
    #display notification number on menu item only for holidays on which we must do an action 
    @api.model
    def _needaction_domain_get(self):
        dom = super(hr_holidays, self)._needaction_domain_get()
        dom.extend(['|',('manager_user_id','=',self._uid),('manager_user_id2','=',self._uid)])
        return dom
    
#add fields to automate selection of good holiday type
class hr_holidays_status(models.Model):
    _inherit = "hr.holidays.status"
    
    _order = 'sequence'
    
    sequence = fields.Integer("Sequence", help='Sequence is used to choose the first type with remaining days as default type.') 
    count = fields.Boolean("Count", help="First type with 'count' and with several remaining days will be used as default type ")
    
