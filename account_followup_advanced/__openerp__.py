# -*- coding: utf-8 -*-

{
    'name': 'Account Followup Advanced',
    'version': '0.1',
    'category': 'Accounting',
    'description': "Allow the selection of Partners during automated process",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['account_followup'],
    "data" : ['wizard/account_followup_print_view.xml',
              'account_followup_customers.xml',
              'views/report_followup.xml'
        ],
    'installable': True,
    'auto_install': False,
    'application': False,

}
