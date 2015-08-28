# -*- coding: utf-8 -*-

{
    'name': 'Elneo sale price update',
    'version': '8.0.1.0.0',
    'category': 'Sales & Purchases',
    'sequence': 1,
    'summary': '',
    'description': """
        Update sale price of each line
    """,
    'author':  'Elneo',
    'website': 'www.elneo.com',
    'depends': ['sale',],
    'data': ['views/elneo_sale_price_update_view.xml',],
    'installable': True,
    'auto_install': False,
    'application': False,
}
