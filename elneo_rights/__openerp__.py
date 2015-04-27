# -*- coding: utf-8 -*-

{
    'name': 'Elneo rights',
    'version': '0.1',
    'category': 'Base',
    'description': "Manage rights for elneo : all elneo's modules must depends on this module. And for each other modules we must inherit views.",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['stock'],
    "data" : ['security/elneo_rights_security.xml','views/elneo_rights_view.xml'],
    'installable': True,
    'auto_install': False,
    'application': False,

}
