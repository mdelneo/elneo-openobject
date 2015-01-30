# -*- coding: utf-8 -*-
{
    'name': 'Elneo prospect',
    'version': '0.1',
    'category': 'Sale',
    'description': "Add notion of prospect. If a partner is prospect, a new sale create invoice before delivery. And when sale is unblocked the partner became a customer (prospect = False)",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': [],
    'data' : ['elneo_prospect_view.xml'],
    'installable': True,
    'auto_install': False,
    'application': True,
}