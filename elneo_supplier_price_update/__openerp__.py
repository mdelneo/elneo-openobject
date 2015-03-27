# -*- coding: utf-8 -*-
{
    'name': 'Elneo Supplier Price Update',
    'version': '0.1',
    'category': 'Elneo',
    'description': "Make easier the supplier prices update",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['base','account','purchase','product','elneo_autocompute_webshop'],
    "update_xml" : ['price_update.xml','price_update_sequence.xml','price_update_workflow.xml','price_update_line_workflow.xml','security/ir.model.access.csv','elneo_landefeld_price_update.xml', 'price_update_data.xml','product_view.xml','wizard/supplier_price_update_wizard_view.xml'],
    'installable': True,
    'active': False,
}