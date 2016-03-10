# -*- coding: utf-8 -*-

{
    'name': 'Elneo Purchase',
    'version': '0.1',
    'category': 'Purchase',
    'description': "Adapt purchase to elneo specifics",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['purchase','sale','purchase_sale','elneo_stock'],
    "data" : ['views/elneo_purchase_view.xml','views/res_config.xml','security/ir.model.access.csv',
              'wizard/purchase_group_view.xml'],
    'installable': True,
    'auto_install': False,
    'application': False,

}
