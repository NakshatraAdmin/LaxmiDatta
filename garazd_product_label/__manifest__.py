{
    'name': 'Custom Product Labels',
    'version': '17.0.1.4.0',
    'category': 'Extra Tools',
    "author": "7span",
    "website": "https://www.7span.com",
    'license': 'LGPL-3',
    'summary': 'Print custom product labels with barcode | Barcode Product Label',
    'images': ['static/description/banner.png', 'static/description/icon.png'],
    'depends': [
        'product', 'stock'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/product_data.xml',
        'data/print_label_type_data.xml',
        'data/ir_filters_data.xml',
        'report/product_label_reports.xml',
        'report/product_label_templates.xml',
        'wizard/print_product_label_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'demo': [
        'demo/product_demo.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
