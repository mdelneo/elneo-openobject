# -*- coding: utf-8 -*-

{
    'name': 'Purchase invoice validation',
    'version': '0.1',
    'category': 'Elneo',
    'description': "Module to help validation of purchase invoices.",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['account'],
    "data" : [
        "views/purchase_invoice_validation_view.xml",
        "security/ir.model.access.csv",
    ],
    'installable': True,
    'active': False,
}
