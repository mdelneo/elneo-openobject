# -*- coding: utf-8 -*-

{
    'name': 'Elneo account',
    'version': '0.1',
    'category': 'Sale',
    'description': "Adapt accounting flows to elneo specifics",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['base','account','sale','purchase','elneo_purchase', 'sale_layout','elneo_crm','elneo_sale','purchase_invoice_validation','account_invoice_merge','stock_picking_invoice_link','account_cost_price'],
    "data" : ['views/elneo_account_view.xml',
              'views/sale_view.xml',
              'views/purchase_view.xml',
              'views/product_view.xml',
              'wizard/payment_term_alert_wizard_view.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': False,

}
