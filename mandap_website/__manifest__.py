{
    'name': 'Mandap Website',
    'version': '17.0.1.0.0',
    'category': 'Website',
    'summary': 'Custom Homepage for Mandap Website',
    'description': """
        Mandap Website Homepage Module
        ==============================
        - Custom professional homepage design
        - Featured mandap designs gallery
        - Services showcase
        - Testimonials section
    """,
    'author': 'LaxmiDatta',
    'website': 'https://www.nakshatra.com',
    'depends': [
        'website',
        'website_sale',
        'product',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/mandap_design_views.xml',
        'views/mandap_color_views.xml',
        'views/product_category_views.xml',
        'views/product_template_views.xml',
        'views/shop_template.xml',
        'views/homepage_template.xml',
        'data/homepage_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'mandap_website/static/src/css/mandap_homepage.css',
            'mandap_website/static/src/css/mandap_shop.css',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
