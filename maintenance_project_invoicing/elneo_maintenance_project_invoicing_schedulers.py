from osv import osv
from datetime import datetime

def add_one_year(d):
    if d:
        return str(int(d.split('-')[0])+1)+'-'+d.split('-')[1]+'-'+d.split('-')[2]
    return ''
def add_one_month(d):
    d.split('-')[0]
    init_year = d.split('-')[0]
    init_month = d.split('-')[1]
    init_day = d.split('-')[2]
    if init_month == '12':
        return str(int(init_year)+1)+'-01-'+init_day
    return init_year+'-'+str(int(init_month)+1)+'-'+init_day

class scheduler_check_landefeld(osv.osv):
    _name = 'scheduler.maintenance_project'
    
    def generate_maintenance_project_invoice(self, cr, uid, ids=False, context=None):
        project_pool = self.pool.get("maintenance.project")
        projects_to_invoice_id = project_pool.search(cr, uid, [('next_invoice_date','<=',datetime.strftime(datetime.today(), '%Y-%m-%d')), ('state','=','active')])
        project_pool.generate_next_invoice(cr, uid, projects_to_invoice_id, context=context)
        
        for project in project_pool.browse(cr, uid, projects_to_invoice_id, context):
            if project.invoicing_delay == 'monthly':
                new_next_invoice_date = add_one_month(project.next_invoice_date)
            else:
                new_next_invoice_date = add_one_year(project.next_invoice_date)
                
            values = {'next_invoice_date':new_next_invoice_date}
            
            #if new invoice date > end date of project, increase it
            if project.date_end and (project.date_end < new_next_invoice_date):
                if project.invoicing_delay == 'monthly':
                    values["date_end"] =  add_one_month(project.date_end)
                else:
                    values["date_end"] =  add_one_year(project.date_end)
                    
            project_pool.write(cr, uid, [project.id], values)
            
        return True
    
scheduler_check_landefeld()