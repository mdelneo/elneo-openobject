# -*- coding: utf-8 -*-
{
    'name' : 'Production Server',
    'version' : '1.0',
    'author' : 'Elneo',
    'category' : 'Global',
    'description' : """

Set production server address
    """,
    'website': 'https://www.elneo.com',
    'depends' : ['base_setup'],
    'data': ['production_server_view.xml'
    ],
    
    'installable': True,
    'auto_install': False,
    'application': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
