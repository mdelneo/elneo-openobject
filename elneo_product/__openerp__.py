# -*- coding: utf-8 -*-

{
    'name': 'Elneo Product',
    'version': '0.1',
    'category': 'Stock',
    'description': "Adapt product flows to elneo specifics",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['product','stock','elneo_account','sale'],
    "data" : ['views/elneo_product_view.xml'
        ],
    'installable': True,
    'auto_install': False,
    'application': False,

}
