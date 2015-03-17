# -*- coding: utf-8 -*-

{
    'name': 'Sale delivery date',
    'version': '0.1',
    'category': 'Sale',
    'description': "Add scheduled date, and propose to fill it from computed delivery date. It also show the real shipment date.",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['base','sale_stock', 'sale_order_dates'],
    "data" : ['views/sale_delivery_date_view.xml'],
    'installable': True,
    'auto_install': False,
    'application': True,

}
