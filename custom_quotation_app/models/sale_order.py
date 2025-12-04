# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_image_1920 = fields.Image(
        string='Product Image',
        related='product_id.image_1920',
        readonly=True,
    )
    bom_id = fields.Many2one('mrp.bom', string="Bill of Materials", domain="[('product_tmpl_id', '=', product_template_id)]")


class SaleOrder(models.Model):
    _inherit = 'sale.order'


    other_references = fields.Char()
    dispatched_through_id = fields.Many2one('res.partner')
    vehicle_no = fields.Char()
    article= fields.Char(string="ARTICLE NO")