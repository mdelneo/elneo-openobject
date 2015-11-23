# -*- coding: utf-8 -*-

{
    'name': 'Elneo translation',
    'version': '0.1',
    'category': 'Sale',
    'sequence': 150, 
    'description': "Change translations",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['base','stock','product'],
    "data" : ['views/elneo_stock.xml',
              'views/elneo_product.xml'],
    'installable': True,
    'auto_install': False,
    'application': False,

}
