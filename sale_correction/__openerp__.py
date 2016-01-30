# -*- coding: utf-8 -*-

{
    'name': 'Sales Corrections',
    'version': '1.0',
    'category': 'Sale',
    'description': """
        Module to allow user to modify a sale order after confirmation
    """,
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['sale','sale_layout', 'purchase'],
    'data': ['wizard/sale_correction_wizard.xml','wizard/purchase_correction_wizard.xml','sale_view.xml','purchase_view.xml'],
    'installable': True,
    'active': False,
    'application':False
}