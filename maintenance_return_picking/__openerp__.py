# -*- coding: utf-8 -*-

{
    'name': 'Maintenance return picking',
    'version': '0.1',
    'category': 'Elneo',
    'description': "Module to adapt maintenance module to elneo specifics : spare part reserved but not placed by technician",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['maintenance', 'maintenance_product',],
    'data' : [
              'maintenance_return_picking_view.xml',
              'data/install.yml'
        ],
    'installable': True,
    'active': False,
}
