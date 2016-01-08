# -*- coding: utf-8 -*-

{
    'name': 'Elneo stock',
    'version': '0.1',
    'category': 'Stock',
    'description': "Adapt stock flows to elneo specifics",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['base','stock','purchase', 'sale_margin', 'maintenance_product','elneo_rights','elneo_serial_number'],
    "data" : [
              'wizard/transfert_move_wizard_view.xml',
              'wizard/stock_transfer_details.xml', 
              'views/elneo_stock_view.xml',
              'views/user_view.xml',
              'security/ir.model.access.csv'
              ],
    'installable': True,
    'auto_install': False,
    'application': False,

}
