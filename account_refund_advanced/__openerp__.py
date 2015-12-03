# -*- coding: utf-8 -*-

{
    'name': 'Account Refund Advanced',
    'version': '0.1',
    'category': 'Accounting',
    'description': '''Allow creation and validation of new invoice refunds with reconciliation only if there is no existing reconciliation.
    
    ''',
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['account',],
    "data" : ['views/account_view.xml'],
    'installable': True,
    'auto_install': False,
    'application': False,
}
