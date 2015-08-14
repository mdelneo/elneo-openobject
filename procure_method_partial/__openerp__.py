# -*- coding: utf-8 -*-

{
    'name': 'Procure method partial',
    'version': '0.1',
    'category': 'Stock',
    'description': "Add a new move supply method in procurement rules to take everything which can be, from stock, and create a procurement for the rest.",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['stock','purchase'],
    "data" : ['views/procure_method_partial_view.xml','security/ir.model.access.csv'],
    'installable': True,
    'auto_install': False,
    'application': False,

}
