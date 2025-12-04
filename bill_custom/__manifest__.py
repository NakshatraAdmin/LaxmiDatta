# -*- encoding: utf-8 -*-

{
    'name': ' Customization',
    'version': '17.1.0',
    'summary': 'Product Customization',
    'description': 'Product Customization Validation',
    'website': 'https://www.volar.com',
    'author': 'Product Customization',
    'category': 'Inventory/Purchase',
    'depends': ['product', 'purchase','sale'],
    'data': [
    # 'views/product_product_view.xml',
    'views/custom_fields.xml',
    'views/report_saleorder_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

#vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: 
