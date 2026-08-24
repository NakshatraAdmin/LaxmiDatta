# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ProductPricelistHistory(models.Model):
    _name = 'product.pricelist.history'
    _description = 'Product Pricelist History'
    _order = 'id desc'

    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Pricelist',
        ondelete='cascade',
        required=True,
        index=True,
    )
    original_item_id = fields.Integer(
        string='Original Price Rule ID',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product Variant',
        ondelete='set null',
        index=True,
    )
    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product',
        ondelete='set null',
        index=True,
    )
    categ_id = fields.Many2one(
        'product.category',
        string='Product Category',
        ondelete='set null',
    )
    applied_on = fields.Selection(
        selection=[
            ('3_global', 'All Products'),
            ('2_product_category', 'Product Category'),
            ('1_product', 'Product'),
            ('0_product_variant', 'Product Variant'),
        ],
        string='Applied On',
        default='3_global',
    )
    min_quantity = fields.Float(
        string='Min. Quantity',
        default=1.0,
    )
    fixed_price = fields.Float(
        string='Previous Price',
        digits='Product Price',
    )
    compute_price = fields.Selection(
        selection=[
            ('fixed', 'Fixed Price'),
            ('percentage', 'Discount'),
            ('formula', 'Formula'),
        ],
        string='Compute Price',
        default='fixed',
    )
    percent_price = fields.Float(
        string='Percentage Price',
    )
    price_discount = fields.Float(
        string='Price Discount',
    )
    price_surcharge = fields.Float(
        string='Price Surcharge',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='pricelist_id.currency_id',
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='pricelist_id.company_id',
        store=True,
        readonly=True,
    )
    date_start = fields.Datetime(
        string='Start Date',
    )
    date_end = fields.Datetime(
        string='End Date',
    )
    wizard_id = fields.Integer(
        string='Source Bulk Update Order',
    )
