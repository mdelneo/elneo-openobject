# -*- coding: utf-8 -*-

{
    'name': 'Account block partner',
    'version': '0.1',
    'category': 'Accounting',
    'description': '''Allow accounting to block a partner. When a partner is blocked, each deliveries to this partner will be blocked in "blocked" state (instead of "ready state"). 
    Furthermore accounting can explain blocking reasons in partner form.
    Each blocked partner are automatically followed by accounting team, and payment reconciliations on a blocked partner will log messages. 
    Warning message is also displayed when we choose a blocked partner in a sale, or when we confirm a purchase order linked to a sale order for a blocked partner.     
    ''',
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['account','purchase','purchase_sale','account_followup'],
    "data" : ['views/account_block_partner_view.xml',
              'views/template.xml',
              'security/account_block_partner_security.xml',
              'purchase_workflow.xml'
              ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'css': ['static/src/css/base.css'],
}
