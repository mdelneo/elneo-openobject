# -*- coding: utf-8 -*-

{
    'name': 'Elneo HR',
    'version': '0.1',
    'category': 'HR',
    'description': """Adapt hr to elneo specifics : 
        - For holidays : 
            - select automatically the good type depending on remaining days, 
            - change warning windows behavior, 
            - select automatically manager and manager2 depending on manager of department and hr manager.
            - allow days overlap
            - compute days depending on other leaves and working days
            - set default value of days (current day at 08:00 to 16:45)
        - For Equipments : add purchase date
        - For Employees : add several fields for human resources
    """,
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['base','hr_equipment', 'hr_holidays'],
    "data" : ['views/elneo_hr_equipment_view.xml','views/elneo_hr_holidays_view.xml','views/elneo_hr_view.xml'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
