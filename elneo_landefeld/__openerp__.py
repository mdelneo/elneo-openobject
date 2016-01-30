# -*- coding: utf-8 -*-

{
    'name': 'Elneo Landefeld',
    'version': '0.1',
    'category': 'Elneo',
    'description': "Module for outreach with Landefeld",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['purchase','elneo_stock','edi_simple','production_server','edi_opentrans','elneo_crm','partner_firstname','stock_dropshipping'],
    "data" : ['views/sale_view.xml',
              'views/res_config.xml',
              'views/stock_view.xml',
              'views/elneo_web_shop.xml',
              'wizard/landefeld_sale_wizard_view.xml',
              'security/ir.model.access.csv',
              'views/edi_view.xml',
              'elneo_web_shop_sequence.xml'
                    ],
    'installable': True,
    'active': False,
}