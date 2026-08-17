# -*- coding: utf-8 -*-
{
    'name': 'NS Bulk Updation Pricelist',
    'version': '17.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Bulk update product pricelist item rules based on percentage, fixed amount, or fixed price',
    'description': """
Bulk Pricelist Updation
=======================
This module allows Sales Managers and Pricing Administrators to bulk update product pricelist item rules
or generate/update pricelist items for selected products based on specified calculation criteria:
- Percentage Increase/Decrease
- Fixed Amount Addition/Subtraction
- Set Fixed Price

Criteria Filters:
- All Products
- Product Category
- Specific Products
- Selected Pricelist Items
    """,
    'author': 'Nakshatra',
    'license': 'LGPL-3',
    'depends': [
        'sale',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/bulk_pricelist_update_wizard_views.xml',
        'views/product_pricelist_views.xml',
        'views/product_views.xml',
    ],
    'installable': True,
    'application': False,
}
