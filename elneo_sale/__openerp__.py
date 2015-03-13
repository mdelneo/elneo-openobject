# -*- coding: utf-8 -*-

{
    'name': 'Elneo sale',
    'version': '0.1',
    'category': 'Sale',
    'description': "Adapt sales flows to elneo specifics",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['base','sale','sale_crm','sales_team','elneo_crm'],
    "data" : ['views/elneo_sale_view.xml'
        ],
    'installable': True,
    'auto_install': False,
    'application': True,

}
