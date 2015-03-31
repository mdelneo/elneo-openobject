# -*- coding: utf-8 -*-

{
    'name': 'Elneo account',
    'version': '0.1',
    'category': 'Sale',
    'description': "Adapt accounting flows to elneo specifics",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['base','account','sale'],
    "data" : ['views/elneo_account_view.xml',
              'views/sale_view.xml',
              'views/purchase_view.xml'
        ],
    'installable': True,
    'auto_install': False,
    'application': False,

}
