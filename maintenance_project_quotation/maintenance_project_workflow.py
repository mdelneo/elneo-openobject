#--------------------------------------------------------------------------------------------#
# Elneo S.A.
#
# Module to allow data migration from
#
#--------------------------------------------------------------------------------------------#


from openerp import models, fields, api
from openerp.exceptions import Warning

class maintenance_project_workflow(models.TransientModel):
    _name='maintenance.project.workflow'
    _params={
             'workflow_name':'maintenance.project.basic',
             'workflow_osv':'maintenance.project'
             }


    @api.multi
    def migrate(self):
        self._check_workflow()
        # Loop on every maintenance project
        for maintenance_project in self.env['maintenance.project'].search([]):
            
            # We get the workflow state to define 
            state = self._get_state_to_insert(maintenance_project)
            
            # First table 
            wkf_instance = self._get_instance(maintenance_project)
           
            
           
            instance_tuple={'state':'active','res_type':'maintenance.project','res_id':maintenance_project.id,'wkf_id':self._get_workflow(self._params['workflow_name'], self._params['workflow_osv'])}
            wkf_instance = self._create_instance(instance_tuple)
            if not wkf_instance:
                raise Warning (_('Workflow creation error for project : %s')%(str(maintenance_project.id)))
            
            # Second table    
            wkf_workitem=self._get_wkf_workitem(wkf_instance, self._get_activity( self._get_workflow(self._params['workflow_name'], self._params['workflow_osv']),state))
            
            workitem_tuple = {'inst_id':wkf_instance,'act_id':self._get_activity(self._get_workflow(self._params['workflow_name'], self._params['workflow_osv']), state),'state':'complete'}
            wkf_workitem=self._create_workitem(workitem_tuple)
    
            if not wkf_workitem:
                raise Warning(_('Workflow Workitem creation error for project : %s')%(str(maintenance_project.id)))
                
            if maintenance_project.state != state:
                maintenance_project.state = state

        return {}
    
    # Check if the workflow linked to the resource (the maintenance project) is the
    # correct one (e.g.: if we change workflow name), otherwise delete links
    def _check_workflow(self):
        res=False
      
        wkf_id = self._get_workflow( self._params['workflow_name'], self._params['workflow_osv'])
        
        self.env.cr.execute('select id, wkf_id, res_id from wkf_instance where wkf_id in (select id from wkf where osv = \''+self._params['workflow_osv']+'\')')
        
        for (id,wk_id,res_id) in self.env.cr.fetchall():
            
            wkf_res_id = wk_id
            inst_id=id
            
            self.env.cr.execute('delete from wkf_instance where id=%s',([inst_id]))
            self.env.cr.execute('delete from wkf_workitem where inst_id=%s',([inst_id]))
            self.env.cr.commit()
            res = True
        
            
        
        return res
    

    def _get_instance(self,res_id):
        #wkf_instance = self.pool.get('wkf_instance')
        #res = wkf_instance.search(cr,uid,id,{'res_id':res_id,'wkf_id':self._get_workflow(cr, uid, self._params.workflow_name, self._params.workflow_osv, context)})
        res = None
        self.env.cr.execute('select id from wkf_instance where wkf_id=%s and res_id=%s', (self._get_workflow(self._params['workflow_name'], self._params['workflow_osv'],),res_id.id))
        
        for(id,) in self.env.cr.fetchall():
            res = id
        
        return res
    
    def _get_wkf_workitem(self,inst_id,act_id):
       
        res = None
        self.env.cr.execute('select id from wkf_workitem where inst_id=%s and act_id=%s', (inst_id,act_id))
        
        for(id,) in self.env.cr.fetchall():
            res = id
        
        return res
    
    
    def _create_instance(self,instance_tuple):
        res=None
        
        self.env.cr.execute('insert into wkf_instance(uid,state,res_type,res_id,wkf_id) VALUES (%s,%s,%s,%s,%s)', (self.env.user.id,instance_tuple['state'],instance_tuple['res_type'],instance_tuple['res_id'],instance_tuple['wkf_id']))
        
        self.env.cr.commit()
        
        self.env.cr.execute('SELECT max(id) FROM wkf_instance')
        
        for (id,) in self.env.cr.fetchall():
            res = id
       
        return res
    
    def _create_workitem(self,workitem_tuple):
        res=None
         
        
        self.env.cr.execute('insert into wkf_workitem(act_id,inst_id,state) VALUES (%s,%s,%s)', (workitem_tuple['act_id'],workitem_tuple['inst_id'],workitem_tuple['state']))
        
        self.env.cr.commit()
        
        self.env.cr.execute('SELECT max(id) FROM wkf_workitem')
        
        for (id,) in self.env.cr.fetchall():
            res = id
       
        return res
    
    def _get_workflow(self,name=None,osv=None):
        res=None
        
        if not name:
            name=self._params['workflow_name']
        if not osv:
            osv=self._params['workflow_osv']
                
        self.env.cr.execute('select id from wkf where name=%s and osv=%s', (name, osv))
        
        for(id,) in self.env.cr.fetchall():
            res = id
        
        return res
    
    def _get_activity(self,wkf_id,name):
        res=None
        
        self.env.cr.execute('select id from wkf_activity where wkf_id=%s and name=%s', (wkf_id, name))
        
        for(id,) in self.env.cr.fetchall():
            res = id
        
        return res
    
    #Looking for current state if defined
    #If not, check the enable value
    #Otherwise, define to draft

    def _get_state_to_insert(self,res_id):
        res='draft'
        
        if res_id.state:
            id = self._get_workflow()
            self.env.cr.execute('select id, name, wkf_id from wkf_activity where wkf_id = %s',(id,))
            
            for (id,name,wkf_id) in self.env.cr.fetchall():
                if (name == res_id.state):
                    res=res_id.state
                    break
        else:
            if (res_id and res_id.enable):
                res='active'
            elif(res_id and not res_id.enable):
                res='disabled'
        
        return res

    