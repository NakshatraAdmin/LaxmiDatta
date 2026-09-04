# -*- coding: utf-8 -*-
{
    'name': 'CRM Customisation',
    'version': '17.0.1.1.0',
    'category': 'CRM',
    'summary': 'Allows to Lead sales commission based on Product.',
    'description': """  Allows to Lead sales commission based on Product """,
    'author': 'Nakshatra Techno Solutions',
    'company': 'Nakshatra Techno Solutions',
    'maintainer': 'Nakshatra Techno Solutions',
    'website': 'https://www.nakshatra.com/',
    'depends': ['base','crm','hr'],
    'data': [
        'views/crm_lead_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
