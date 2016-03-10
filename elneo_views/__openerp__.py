# -*- coding: utf-8 -*-
{
    'name': 'Elneo views',
    'version': '0.1',
    'category': '',
    'description': "Adapt views to elneo specifics",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['base','maintenance','maintenance_model','maintenance_product', 
                'maintenance_failure_type', 'maintenance_todo', 'maintenance_serial_number', 
                'elneo_maintenance'],
    "data" : ['views/maintenance_view.xml'],
    'installable': True,
    'auto_install': False,
    'application': False,
}