# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductProduct(models.Model):
    """Expose this module's secondary-UoM settings on product variants.

    The invoice, BOM, and stock customizations work with ``product.product``.
    The settings themselves are stored on ``product.template``, so variants
    must explicitly expose these related fields.
    """

    _inherit = 'product.product'

    is_need_secondary_uom = fields.Boolean(
        related='product_tmpl_id.is_need_secondary_uom',
        readonly=True,
    )
    sec_uom_id = fields.Many2one(
        'uom.uom',
        related='product_tmpl_id.sec_uom_id',
        readonly=True,
    )
    sec_uom_ratio = fields.Float(
        related='product_tmpl_id.sec_uom_ratio',
        readonly=True,
    )
