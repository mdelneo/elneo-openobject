# -*- coding: utf-8 -*-

{
    'name': 'Maintenance Project',
    'version': '0.1',
    'category': 'Maintenance Project',
    'description': "Module to manage maintenance projects (contracts and rentability of maintenance installation).",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['maintenance', 'maintenance_product', 'sale','maintenance_timeofuse'],
    'data': ['maintenance_project_view.xml',
                   'maintenance_project_sequence.xml',
                    'security/ir.model.access.csv',
                     'maintenance_project_workflow.xml',
                      'maintenance_project_data.xml'],
    'installable': True,
    'active': False,
    'application':False
}
