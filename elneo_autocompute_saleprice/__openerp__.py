# -*- coding: utf-8 -*-
{
    'name': 'Elneo autocompute sale price',
    'version': '0.1',
    'website' : 'http://elneo.com',
    'category': '',
    'summary': '',
    'description': "",
    'author': 'Elneo',
    'depends': ['sale', 'purchase', 'elneo_default_supplier', 'sale_stock'],
    'data': [
        'views/elneo_autocompute_saleprice_view.xml','views/customer_discount_view.xml'
    ],
    'installable': True,
    'auto_install': False,
}
