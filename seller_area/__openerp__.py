# -*- coding: utf-8 -*-

{
    'name': 'Seller Area',
    'version': '0.1',
    'category': 'Sale',
    'description': "Define a sector by seller, by sales department, for a range of zip code, to select good seller depending on delivery address.",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['sale','crm','sales_team'],
    "data" : ['views/seller_area_view.xml','views/sale_view.xml','security/ir.model.access.csv'],
    'installable': True,
    'auto_install': False,
    'application': True,

}
