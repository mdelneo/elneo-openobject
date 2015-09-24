# -*- coding: utf-8 -*-

{
    'name': 'Maintenance Project Invoicing',
    'version': '0.1',
    'category': 'Maintenance',
    'description': "Generate automatically maintenance project (contract) invoices",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['maintenance_project'],
    "data" : [
        'maintenance_project_invoicing_view.xml',
        'maintenance_project_invoicing_data.xml'
        ],
    'installable': True,
    'active': False,
    'application':True
}
