# -*- coding: utf-8 -*-

{
    'name': 'Elneo report',
    'version': '0.1',
    'category': 'Accounting',
    'description': '''Inheritance of all reports.''',
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['report','sale', 'purchase', 'stock'],
    "data" : ['report/elneo_report_invoice_view.xml',
              'report/elneo_report_maintenance_view.xml',
              'report/elneo_report_purchase_view.xml',
              'report/elneo_report_sale_view.xml',
              'report/elneo_report_stock_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'css': [''],
}
