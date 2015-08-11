# -*- coding: utf-8 -*-
##################################################################################
#
# Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)
# and 2004-2010 Tiny SPRL (<http://tiny.be>).
#
# $Id: hr.py 4656 2006-11-24 09:58:42Z Cyp $
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU Affero General Public License as
#     published by the Free Software Foundation, either version 3 of the
#     License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU Affero General Public License for more details.
#
#     You should have received a copy of the GNU Affero General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models,fields,api, _, workflow
from datetime import datetime, timedelta
from openerp import exceptions

class hr_holidays(models.Model):
    _inherit = "hr.holidays"
    
    @api.model
    def _get_default_status_id(self):
        employee_ids = self.env['hr.employee'].search([('user_id', '=', self._uid)])
        
        if employee_ids:
            employee_id = employee_ids[0]
        else:
            return None
        
        #check by type of holidays if user has always
        type_ids = self.env["hr.holidays.status"].search([])
        
        if not type_ids:
            return None
        
        types = self.env["hr.holidays.status"].browse(type_ids)
        
        for type in types:
            if type.count:
                self._cr.execute("select sum(number_of_days) from hr_holidays where holiday_status_id=%s and state='validate' and employee_id=%s",(type.id, employee_id))
                count = self._cr.fetchone()[0] or 0
                if count > 0:
                    return type.id
        return types[0].id                
                
    def _get_employee(self,cr,uid,ids, context=None):
        if ((uid == 27 or uid == 37) or (not uid)):
            return False
        else:
            ids_employee = self.env['hr.employee'].search(cr, uid, [('user_id','=', uid)])
            return ids_employee[0]    
    
    def onchange_type(self, cr, uid, ids, holiday_type):
        result = {}
        if holiday_type == 'employee':
            if(uid == 27 or uid == 37):
                return result
            ids_employee = self.env['hr.employee'].search(cr, uid, [('user_id','=', uid)])
            if ids_employee:
                result['value'] = {
                    'employee_id': ids_employee[0]
                }
        return result
        
    
    def onchange_date_from(self, cr, uid, ids, date_to, date_from, employee_id):
        result = {}
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
    
    def _get_number_of_days_elneo(self, cr, uid, date_from, date_to, employee_id):
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
        previous_holidays_ids = self.search(cr, uid, [('state','=','validate'),('type','=','remove'),('employee_id','=',employee_id),
                '|','&',('date_from','>=',datetime.strftime(from_date, DATETIME_FORMAT)),('date_from','<=',datetime.strftime(to_date, DATETIME_FORMAT)),
                '|','&',('date_to','>=',datetime.strftime(from_date, DATETIME_FORMAT)),('date_to','<=',datetime.strftime(to_date, DATETIME_FORMAT)),
                '&',('date_from','<=',datetime.strftime(from_date, DATETIME_FORMAT)),('date_to','>=',datetime.strftime(to_date, DATETIME_FORMAT))
        ])
        previous_holidays_objs = self.browse(cr, uid, previous_holidays_ids)
        
        
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
            

    def holidays_confirm(self, cr, uid, ids, *args):
        id_holidays = []
        id_allocation = []
        
        for hr_holiday in self.env["hr.holidays"].browse(cr, uid, ids):
            if hr_holiday.type!="remove":
                id_allocation.append(hr_holiday.id)
            else:
                if not(uid == 27 or uid == 37 or uid == hr_holiday.employee_id.user_id.id or (hr_holiday.department_id and hr_holiday.department_id.manager_id and hr_holiday.department_id.manager_id.user_id and hr_holiday.department_id.manager_id.user_id.id==uid)):
                    raise exceptions.AccessDenied(_('You cannot confirm this holidays !'))
                
                #Ask manager for the first validation
                manager_id=None
                email_to = None
                if hr_holiday.department_id and hr_holiday.department_id.manager_id and hr_holiday.department_id.manager_id.user_id and hr_holiday.department_id.manager_id.user_id.user_email:
                    email_to = hr_holiday.department_id.manager_id.user_id.user_email
                    manager_id = hr_holiday.department_id.manager_id.id
                if not email_to:
                    email_to = 'iba@elneo.com'
                
                body = _("Holiday request for %s received")%(hr_holiday.employee_id.name)
                body += "\n"+"http://erp.elneo.com:8080/openerp/menu?active=428#url=%2Fopenerp%2Fform%2Fedit%3Fmodel%3Dhr.holidays%26id%3D"+str(hr_holiday.id)
                
                self.env["email_template.mailbox"].create(cr, uid, {
                        'email_from':'support@elneo.com', 
                        'email_to':email_to,  
                        'subject':"Holiday Request", 
                        'body_text':body,
                        'account_id':1, 
                    })
                
                super(hr_holidays, self).holidays_confirm(cr, uid, [hr_holiday.id], args)
                if manager_id:
                    self.env["hr.holidays"].write(cr,uid,[hr_holiday.id], {'manager_id':manager_id,'manager_id2':20})
  
        if id_allocation:
            self.write(cr, uid, id_allocation, {'state':'validate'})  
            
            
    def holidays_refuse_manual(self, cr, uid, ids, *args):
        for holiday_id in ids:
            workflow.trg_validate(uid, 'hr.holidays', holiday_id, 'refuse', cr)
        return self.holidays_refuse(cr, uid, ids)
                       
    def holidays_refuse(self, cr, uid, ids, *args):
        for hr_holiday in self.env["hr.holidays"].browse(cr, uid, ids):
            if hr_holiday.type!="remove":
                super(hr_holidays, self).holidays_refuse(cr, uid, [hr_holiday.id], args)
            
            #Check if can validate
            #if not(uid == 27 or uid == 37 or uid == hr_holiday.employee_id.user_id.id or (hr_holiday.department_id and hr_holiday.department_id.manager_id and hr_holiday.department_id.manager_id.user_id and hr_holiday.department_id.manager_id.user_id.id==uid)):
            if not(uid == 27 or uid == 37 or (uid == hr_holiday.employee_id.user_id.id and not(hr_holiday.state in ['validate','validate1'])) or (hr_holiday.department_id and hr_holiday.department_id.manager_id and hr_holiday.department_id.manager_id.user_id and hr_holiday.department_id.manager_id.user_id.id==uid)):
                raise exceptions.AccessDenied(_('You cannot refuse this holidays !'))
            
            if hr_holiday.employee_id and hr_holiday.employee_id.user_id and hr_holiday.employee_id.user_id.user_email:
                email_to = hr_holiday.employee_id.user_id.user_email
                body = _("Holiday request for %s received")%(hr_holiday.employee_id.name)
                body += "\n"+"http://erp.elneo.com:8080/openerp/menu?active=428#url=%2Fopenerp%2Fform%2Fedit%3Fmodel%3Dhr.holidays%26id%3D"+str(hr_holiday.id)
                
                self.env["email_template.mailbox"].create(cr, uid, {
                        'email_from':'support@elneo.com', 
                        'email_to':email_to,  
                        'subject':"Holiday Request", 
                        'body_text':body,
                        'account_id':1, 
                    })
            super(hr_holidays, self).holidays_refuse(cr, uid, [hr_holiday.id], args)
            self.env["hr.holidays"].write(cr,uid,[hr_holiday.id], {'manager_id':None,'manager_id2':None})
        return True
              
    
    def holidays_validate(self, cr, uid, ids, *args):                    
        #Ask manager for the second validation to iba
        email_to = 'iba@elneo.com'
        for hr_holiday in self.env["hr.holidays"].browse(cr, uid, ids):
            if hr_holiday.type!="remove":
                continue
            
            #Check if can validate
            if not(uid == 27 or uid == 37 or (hr_holiday.department_id and hr_holiday.department_id.manager_id and hr_holiday.department_id.manager_id.user_id and hr_holiday.department_id.manager_id.user_id.id==uid)):
                raise exceptions.AccessDenied(_('You cannot validate this holidays !'))
            
            body = _("Holiday request for %s received")%(hr_holiday.employee_id.name)
            body += "\n"+"http://erp.elneo.com:8080/openerp/menu?active=428#url=%2Fopenerp%2Fform%2Fedit%3Fmodel%3Dhr.holidays%26id%3D"+str(hr_holiday.id)
            
            self.env["email_template.mailbox"].create(cr, uid, {
                    'email_from':'support@elneo.com', 
                    'email_to':email_to,  
                    'subject':"Holiday Request", 
                    'body_text':body,
                    'account_id':1, 
                })
            
            super(hr_holidays, self).holidays_validate(cr, uid, [hr_holiday.id], args)
            self.env["hr.holidays"].write(cr,uid,[hr_holiday.id], {'manager_id2':20})
        return True

    def holidays_validate2(self, cr, uid, ids, *args):
        #if not iba raise error
        if uid != 27 and uid != 37:
            raise exceptions.AccessDenied(_('You cannot validate this holidays !'))
        
        
        #Send mail to user - recept email
        for hr_holiday in self.env["hr.holidays"].browse(cr, uid, ids):
            if hr_holiday.type!="remove":
                continue
            
            if hr_holiday.employee_id and hr_holiday.employee_id.user_id and hr_holiday.employee_id.user_id.user_email:
                email_to = hr_holiday.employee_id.user_id.user_email
            
                body = "One of your holiday request has been approved !"
                body += "\n"+"http://erp.elneo.com:8080/openerp/menu?active=428#url=%2Fopenerp%2Fform%2Fedit%3Fmodel%3Dhr.holidays%26id%3D"+str(hr_holiday.id)
                
                self.env["email_template.mailbox"].create(cr, uid, {
                        'email_from':'support@elneo.com', 
                        'email_to':email_to,  
                        'subject':"Holiday Request", 
                        'body_text':body,
                        'account_id':1, 
                    })
        
        return super(hr_holidays, self).holidays_validate2(cr, uid, ids, args)  
    
    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        if not employee_id:
            return {}
        comp = self.env['hr.employee']._get_days(cr, uid, [employee_id], ['days_remaining','days_total'], None, context)
        return {'value':comp[employee_id]}
    
    def _get_year(self, cr, uid, ids, fields, args, context=None):
        res = {}
        for holiday in self.browse(cr, uid, ids, context):
            if holiday.date_from:
                res[holiday.id] = int(holiday.date_from[0:4])
            else:
                res[holiday.id] = 0
        return res
            
    manager_user_id1 = fields.Many2one(related='manager_id.user_id', string='User'),
    manager_user_id2 = fields.Many2one(related='manager_id2.user_id', string='User'),
    days_remaining = fields.Float(related='employee_id.days_remaining', string='Days remaining', readonly=True),
    days_total = fields.Float(related='employee_id.days_total', string='Days total', readonly=True),
    year = fields.Selection([('2014','2014'),('2015','2015'),('2016','2016')], compute='_get_year', string='Year', store=True)
    
    @api.model
    def default_get(self, fields):
        res = super(hr_holidays, self).default_get(fields)
        for field in fields:
            if field == 'name':
                res['name'] = _('Holidays')
            if field == 'holiday_status_id':
                res['holiday_status_id'] = self._get_default_status_id()
            if field == 'date_from':
                res['date_from'] = lambda *a: datetime.now().strftime('%Y-%m-%d 08:00:00')
            if field == 'date_to':
                res['date_to'] = lambda *a: datetime.now().strftime('%Y-%m-%d 16:45:00')
            if field == 'employee_id':
                res['employee_id'] = self._get_employee()
        return res 
    
    
hr_holidays()

class hr_holidays_status(models.Model):
    _inherit = "hr.holidays.status"
    
    _order = 'sequence'
    
    sequence = fields.Integer("Sequence", help='Sequence is used to choose the first type with remaining days as default type.') 
    count = fields.Boolean("Count", help="First type with 'count' and with several remaining days will be used as default type ")
    
hr_holidays_status()