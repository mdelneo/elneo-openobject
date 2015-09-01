# -*- coding: utf-8 -*-

{
    'name': 'Shop Sale',
    'version': '0.1',
    'category': 'Sale',
    'description': "Adapt sales flows to counter specifics",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['sale_stock','account'],
    "data" : ['views/sale_view.xml','views/stock_view.xml','security/sale_security.xml','shop_sale_workflow.xml'
        ],
    'installable': True,
    'auto_install': False,
    'application': False,

}
