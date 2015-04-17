# -*- coding: utf-8 -*-

{
    'name': 'Elneo sale',
    'version': '0.1',
    'category': 'Sale',
    'description': "Adapt sales flows to elneo specifics",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
<<<<<<< Upstream, based on branch '8.0' of https://github.com/Elneo-group/elneo-openobject
    'depends': ['base','sale','delivery','sale_margin','sale_crm','sales_team','elneo_crm','product','sale_stock'],
=======
    'depends': ['base','sale','sale_margin','sale_crm','sales_team','elneo_crm','product','sale_stock'],
>>>>>>> 0e71414 vue des ventes : ajout du tab historique et raccourcis en haut à droite
    "data" : ['views/elneo_sale_view.xml'
        ],
    'installable': True,
    'auto_install': False,
    'application': True,

}
