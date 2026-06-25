# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductCategory(models.Model):
    _inherit = 'product.category'

    image = fields.Image('Category Image', max_width=1920, max_height=1920)
    description = fields.Html('Description', sanitize_attributes=False)
    show_on_homepage = fields.Boolean('Show on Homepage', default=False,
                                      help='Check this to display this category on the homepage')
