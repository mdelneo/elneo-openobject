# -*- coding: utf-8 -*-

{
    'name': 'Stock Retrun Picking Advanced',
    'version': '0.1',
    'category': 'Stock',
    'description': "Allows to automate stock returns (and force availability - the case you have products in hand). Generates draft invoice automatically when you finish return",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['stock'],
    "data" : [
              
              'views/res_config.xml'
              ],
    'installable': True,
    'auto_install': False,
    'application': False,

}
