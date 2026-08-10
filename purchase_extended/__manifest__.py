{
    "name": "Purchase Product Configurator",
    "version": "17.0.1.0.0",
    "category": "Purchases",
    "summary": "Use the sales-style product variant configurator on purchase orders",
    "depends": ["purchase_product_matrix", "sale_product_configurator"],
    "data": [
        "views/purchase_order_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "purchase_extended/static/src/js/purchase_product_field.js",
        ],
    },
    "installable": True,
    "license": "LGPL-3",
}
