# -*- coding: utf-8 -*-

{
    'name': 'CPI belgium',
    'version': '0.1',
    'category': 'Accounting',
    'description': "List of Consumer price index (CPI) daily downloaded from economie.fgov.be",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': [],
    "data" : [
        'cpi_be_view.xml',
        'cpi_be_data.xml',
        'security/ir.model.access.csv'  
        ],
    'installable': True,
    'auto_install': False,
    'application': True,

}
