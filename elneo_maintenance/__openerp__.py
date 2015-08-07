# -*- coding: utf-8 -*-

{
    'name': 'Elneo maintenance',
    'version': '0.1',
    'category': 'Elneo',
    'description': "Module to adapt maintenance module to elneo specifics",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': [ 'maintenance_product',  'elneo_stock'],
    "update_xml" : [
        'elneo_maintenance.xml'
        ],
    'installable': True,
    'active': False,
}
