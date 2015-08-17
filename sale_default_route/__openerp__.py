# -*- coding: utf-8 -*-

{
    'name': 'Sale Default Route',
    'version': '0.1',
    'category': 'Sale',
    'description': "Define default Routes for Sale Order Line depending on stock level",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['sale','sale_stock'],
    "data" : ['views/res_config.xml'],
    'installable': True,
    'auto_install': False,
    'application': False,

}
