# -*- coding: utf-8 -*-

{
    'name': 'Sales Commission',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': """To Create Sales Commission for Sales Person.""",
    'description': """Allows to create sales commission based on Product, 
    Partner, and Discount of Sale order to the sales person.""",
    'author': 'Nakshatra Techno Solutions',
    'company': 'Nakshatra Techno Solutions',
    'maintainer': 'Nakshatra Techno Solutions',
    'website': 'https://www.nakshatra.com/',
    'depends': ['sale_management', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'security/groups.xml',
        'wizard/sales_commission_report_views.xml',
        'views/commission_lines_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/sales_commission_views.xml',
        'views/sales_commission_menus.xml',
        'report/sales_commission_action.xml',
        'report/sales_commission_templates.xml',
    ],
    
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
