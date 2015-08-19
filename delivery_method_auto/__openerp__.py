# -*- coding: utf-8 -*-

{
    'name': 'Delivery method auto',
    'version': '0.1',
    'category': 'Stock',
    'description': "When a delivery method is choose in a sale order, order line is automatically added. Furthermore, we can choose default delivery method in sale configuration.",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['delivery'],
    "data" : ['views/delivery_method_auto_view.xml', 'views/res_config.xml'],
    'installable': True,
    'auto_install': False,
    'application': False,

}
