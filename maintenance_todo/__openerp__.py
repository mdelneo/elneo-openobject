# -*- coding: utf-8 -*-

{
    'name': 'Maintenance Todo',
    'version': '0.1',
    'category': 'Maintenance',
    'description': "Module to manage maintenance todo's linked to an installation.",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['maintenance'],
    'data': [
             'maintenance_todo_view.xml',
             'maintenance_todo_sequence.xml',
             'todo_data.xml',
             'todo_workflow.xml',
             'security/ir.model.access.csv',
             'wizard/todo_wizard_view.xml' ],
    'installable': True,
    'active': False,
    'application':False
}
