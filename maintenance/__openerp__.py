# -*- coding: utf-8 -*-

{
    'name': 'Maintenance',
    'version': '0.1',
    'category': 'Maintenance',
    'description': "Module to manage maintenance.",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['product', 'project', 'sale','stock'],
    'data': ['security/maintenance_security.xml','maintenance_view.xml','maintenance_sequence.xml', 'security/ir.model.access.csv', 'installation_workflow.xml'],
    'installable': True,
    'active': False,
}
