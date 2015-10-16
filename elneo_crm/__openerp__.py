# -*- coding: utf-8 -*-

{
    'name': 'Elneo CRM',
    'version': '0.1',
    'category': 'Sale',
    'description': "Adapt crm to elneo specifics",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['base','email_template','sale_crm','account','sale','partner_firstname','partner_nace','l10n_be_invoice_bba'],
    "data" : ['views/elneo_crm_view.xml', ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
