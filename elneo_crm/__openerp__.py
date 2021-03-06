# -*- coding: utf-8 -*-

{
    'name': 'Elneo CRM',
    'version': '0.1',
    'category': 'Sale',
    'description': "Adapt crm to elneo specifics",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['base','calendar','mail','sales_team','email_template','sale_crm','account','sale','partner_firstname','partner_nace','l10n_be_invoice_bba','account_followup','account_block_partner'],
    "data" : ['views/elneo_crm_view.xml', ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
