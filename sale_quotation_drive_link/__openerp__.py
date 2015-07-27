# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Sale quotation drive link',
    'version': '1.0',
    'category': 'Generic Modules/CRM & SRM',
    'description': """
Insert links of documentation in sale quotations
""",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['sale', 'sale_quotation', 'google_drive_link'],
    'init_xml': [],
    'update_xml': [
        'views/sale_quotation_drive_link_view.xml', 
        'security/ir.model.access.csv','report/report_sale_quotation_drive_link.xml'
    ],
    'demo_xml': [
    ],
    'test': [],
    'installable': True,
    'active': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
