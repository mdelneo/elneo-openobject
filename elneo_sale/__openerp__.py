# -*- coding: utf-8 -*-

{
    'name': 'Elneo sale',
    'version': '0.1',
    'category': 'Sale',
    'description': "Adapt sales flows to elneo specifics",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['product','sale_stock','purchase','purchase_sale','delivery','sale_margin','sale_crm','sales_team','elneo_crm','shop_sale','sale_quotation', 'elneo_report','sale_outgoing_picking_type'],
    "data" : ['views/elneo_sale_view.xml', 'report/elneo_sale_report.xml'
        ],
    'installable': True,
    'auto_install': False,
    'application': True,

}
