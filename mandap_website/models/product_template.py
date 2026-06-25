# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    color_ids = fields.Many2many('mandap.color', string='Colors',
                                 help='Select colors available for this product')
