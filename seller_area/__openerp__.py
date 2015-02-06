# -*- coding: utf-8 -*-

{
    'name': 'Seller Area',
    'version': '0.1',
    'category': 'Sale',
    'description': "Define a sector by seller, by sales department, for a range of zip code, to select good seller depending on delivery address.",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['sale','sales_team'],
    "data" : ['views/seller_area_view.xml','views/sale_view.xml'],
    'installable': True,
    'auto_install': False,
    'application': True,

}
