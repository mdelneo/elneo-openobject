# -*- coding: utf-8 -*-

{
    'name': 'Maintenance Product',
    'version': '0.1',
    'category': 'Maintenance Product',
    'description': "Module to manage products of maintenance.",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['maintenance', 'sale','stock_account','stock'],
    'data': ['wizard/maintenance_update_view.xml',
             'maintenance_product_view.xml',
                   'maintenance_product_sequence.xml', 
                   'security/ir.model.access.csv',
                   'report/report_maintenance.xml', 
                   'data/stock_picking.yml'
                   ],
    'installable': True,
    'active': False,
    'application':False
}
