# -*- coding: utf-8 -*-

{
    'name': 'Elneo HR',
    'version': '0.1',
    'category': 'HR',
    'description': "Adapt hr to elneo specifics",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['base','hr_equipment', 'hr_holidays'],
    "data" : ['views/elneo_hr_equipment_view.xml','views/elneo_hr_holidays_view.xml'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
