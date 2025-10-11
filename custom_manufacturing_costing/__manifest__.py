# -*- coding: utf-8 -*-
{
    'name': "custom_manufacturing_costing",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    'category': 'Uncategorized',
    'version': '0.1',
    'depends': ['base','sale_management','mrp','purchase', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'report/report_overview_template.xml',
        'report/work_order_report.xml',
        'wizard/assign_employee_wizard.xml',
        'views/views.xml',
        'views/operations.xml',
        'views/mrp_production_views.xml',
        'views/mrp_workorder_views.xml',
    ],

    'license': 'LGPL-3',
}
