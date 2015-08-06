# -*- coding: utf-8 -*-

{
    'name': 'Sale outgoing picking type',
    'version': '0.1',
    'category': 'Accounting',
    'description': '''Add outgoing picking type in sale_order
    ''',
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['account','purchase'],
    "data" : ['views/sale_outgoing_picking_type_view.xml'],
    'installable': True,
    'auto_install': False,
    'application': False,
}
