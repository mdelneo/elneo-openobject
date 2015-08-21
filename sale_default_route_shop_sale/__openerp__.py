# -*- coding: utf-8 -*-

{
    'name': 'Sale Default Route Shop Sale',
    'version': '0.1',
    'category': 'Sale',
    'description': "Define default Routes for Sale Order Line for shop sale",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['sale_default_route','shop_sale'],
    "data" : ['views/res_config.xml','views/sale_default_route_shop_sale.xml'],
    'installable': True,
    'auto_install': False,
    'application': False,

}
