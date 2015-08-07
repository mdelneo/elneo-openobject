'''
Created on 29 juil. 2014

@author: elneo
'''
from osv import osv,fields
from datetime import datetime, timedelta

class maintenance_element_timeofuse_wizard_detail(osv.osv_memory):
    _name = 'maintenance.element.timeofuse.wizard.detail'
    
    _columns = {
        'wizard_id':fields.many2one('maintenance.element.timeofuse.wizard.time_of_use', 'Wizard'),
        'date':fields.datetime('Date'),
        'time_of_use':fields.float('Time of Use'),
        
        
    }
maintenance_element_timeofuse_wizard_detail()

class import_timeofuse(osv.osv_memory):
    _name = 'maintenance.element.timeofuse.wizard'
    
    def calculate(self,cr,uid,ids,context=None):
        
        res={'nodestroy':True}
        
        
        for element in self.browse(cr,uid,ids,context=context):
            if (len(element.history) == 2):
                days_diff = abs((datetime.strptime(element.history[0]['date'],'%Y-%m-%d %H:%M:%S')-datetime.strptime(element.history[1]['date'],'%Y-%m-%d %H:%M:%S')).days)
                counters_diff = abs(element.history[0]['time_of_use']-element.history[1]['time_of_use'])
                real_hours = int((counters_diff/days_diff) * 365)
                data={}
                
                
                self.write(cr,uid,ids,{'calc_time':real_hours},context=context)

        return res
    
    def _get_history(self,cr,uid,context=None):
        res = []
        
        if(context and context.has_key('active_ids')):
            element_ids = context['active_ids']
            elements = self.pool.get('maintenance.element').browse(cr,uid,element_ids,context=context)
            tmp=[]
            for element in elements:
                for timeofuse in element.timeofuse_history:
                    tmp.append({'date':timeofuse.date,'time_of_use':timeofuse.time_of_use})
            
            tmp.sort(key=lambda x: x['date'],reverse=True)
            
            if tmp:
                res.append(tmp[0])
            
            #find next date after 10 months
            i = 1
            if len(tmp) > 1:
                while i < len(tmp):
                    if tmp[i]['date'] and tmp[i]['time_of_use'] != 0:
                        if datetime.strptime(tmp[0]['date'],'%Y-%m-%d %H:%M:%S') - datetime.strptime(tmp[i]['date'],'%Y-%m-%d %H:%M:%S') > timedelta(days=300):
                            res.append(tmp[i])
                            return res
                    i = i+1
                #if no date found : use last date
                res.append(tmp[len(tmp)-1])
            
        return res
    
    _columns={
              'history':fields.one2many('maintenance.element.timeofuse.wizard.detail','wizard_id','Time of Use'),
              'calc_time':fields.float('Calculated Time')
              }
    
    _defaults={
               'history':_get_history,
               'calc_time':0
               }
    def import_time(self,cr,uid,ids,context=None):
        res={}
        
        for el in self.browse(cr,uid,ids,context=context):
            self.pool.get('maintenance.element').write(cr,uid,context['active_ids'],{'expected_time_of_use':el.calc_time})
            
        return res
    
    

import_timeofuse()
