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
    'name': 'Product properties',
    'version': '1.0',
    'category': 'Generic Modules/CRM & SRM',
    'description': """
Add product_properties objects, to manage specifications of products. Templates of specifications are defined by product categories. 
""",
    'author': 'Elneo',
    'website': 'http://www.elneo.com',
    'depends': ['product','sale', 'sale_layout'],
    'init_xml': [],
    'update_xml': [
        'views/product_properties_view.xml', 
        'security/ir.model.access.csv'
    ],
    'demo_xml': [
    ],
    'test': [],
    'installable': True,
    'active': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
