# -*- coding: utf-8 -*-

{
    'name': 'Elneo maintenance project invoicing',
    'version': '0.1',
    'category': 'Elneo',
    'description': "Module to adapt maintenance project module to elneo specifics (cron to generate invoice)",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['maintenance_project_invoicing','cpi_be'],
    "update_xml" : [
        'elneo_maintenance_project_invoicing_view.xml',
        'res_config.xml'
        ],
    'installable': True,
    'active': False,
    'application':False
}
