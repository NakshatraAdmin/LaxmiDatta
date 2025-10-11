#############################################################################
# -*- coding: utf-8 -*-
###############################################################################
#
#    BeyonData Solutions Private Limited
#
#    Copyright (C) 2024-TODAY BeyonData Solutions Private Limited
#    Author: Mittal Nayar
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#
###############################################################################

{
    'name':'Avoid Products Duplication',
    'author': 'BeyonData Solutions Private Limited',
    'website': 'https://www.beyondatagroup.com/',
    'license': 'LGPL-3',
    'depends':['base','mail','sale_management'],
    'summary':"Avoid product name duplication or Avoid interal reference duplication or Restrict duplication of the product",
    'description': """Restrict duplication of the products with name or internal reference.""",
    'category':'sales',
    'license': 'LGPL-3',
    'version': '17.0.0.0.0',
    'live_test_url': 'https://www.beyondatagroup.com/contactus',
    'data':[
        'views/duplication_settings.xml',
    ],
    'images': ['static/description/banners.gif'],
}
