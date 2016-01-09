# -*- coding: utf-8 -*-

{
    'name': 'Make unique purchases for orderpoints requests',
    'version': '0.1',
    'category': 'Stock',
    'description': "When searching purchase orders, look for purchases without sales linked",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['stock','procurement','purchase'],
    "data" : ['views/res_config.xml'],
    'installable': True,
    'auto_install': False,
    'application': False,

}
