# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

class MandapWebsite(http.Controller):

    @http.route('/', type='http', auth="public", website=True, sitemap=True)
    def homepage(self, **kw):
        """Custom homepage with featured product categories"""
        ProductCategory = request.env['product.category']
        # Fetch categories that should be shown on homepage
        featured_categories = ProductCategory.search([
            ('show_on_homepage', '=', True)
        ], limit=6, order='name')
        
        return request.render('mandap_website.mandap_homepage', {
            'featured_categories': featured_categories,
        })
