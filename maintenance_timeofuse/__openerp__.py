# -*- coding: utf-8 -*-

{
    'name': 'Maintenance time of use',
    'version': '0.1',
    'category': 'Maintenance',
    'description': "Module to manage time of use of maintenance elements.",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['maintenance', 'maintenance_product'],
    'data': ['maintenance_timeofuse_view.xml','security/ir.model.access.csv', 'wizard/maintenance_timeofuse_wizard.xml','report/maintenance_timeofuse_report.xml'],
    'installable': True,
    'active': False,
    'application':False
}
