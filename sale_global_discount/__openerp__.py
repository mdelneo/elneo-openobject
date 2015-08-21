# -*- coding: utf-8 -*-

{
    'name': 'Sale Global Discount',
    'version': '0.1',
    'category': 'Sale',
    'description': "Add a wizard to change discount on each sale order lines",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['sale'],
    "data" : ['views/sale_global_discount_view.xml','wizard/sale_global_discount_wizard_view.xml'],
    'installable': True,
    'auto_install': False,
    'application': False,

}
