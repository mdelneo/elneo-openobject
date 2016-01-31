# -*- coding: utf-8 -*-

{
    'name': 'EDI Simple',
    'version': '0.1',
    'category': 'Elneo',
    'description': "Module to simplify EDI messages communication flow",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['base','mail','purchase'],
    "data" : [
                    'views/edi_simple_view.xml',
                    'security/ir.model.access.csv',
                    'wizard/edi_import_wizard.xml',
                    'wizard/edi_process_wizard.xml',
                    'edi_simple_data.xml',
                    'views/purchase_view.xml',
                    'data/edi_simple_data.xml'
                    ],
    'qweb' : [
              'static/src/xml/edi.xml'
              ],
    'js': [ 'static/src/js/edi.js',   ],
    'installable': True,
    'active': False,
    'application':False
}
