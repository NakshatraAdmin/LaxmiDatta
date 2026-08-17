# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    pricelist_rule_ids = fields.One2many(
        string="Pricelist Rules",
        comodel_name='product.pricelist.item',
        inverse_name='product_tmpl_id',
        domain=lambda self: self._domain_pricelist_rule_ids(),
    )

    def _base_domain_item_ids(self):
        return [
            '|',
            ('pricelist_id', '=', False),
            ('pricelist_id.active', '=', True),
        ]

    def _domain_pricelist_rule_ids(self):
        return self._base_domain_item_ids()


class ProductProduct(models.Model):
    _inherit = 'product.product'

    pricelist_rule_ids = fields.One2many(
        string="Pricelist Rules",
        comodel_name='product.pricelist.item',
        inverse_name='product_id',
        compute='_compute_pricelist_rule_ids',
        inverse='_inverse_pricelist_rule_ids',
        readonly=False,
    )

    @api.depends('product_tmpl_id.pricelist_rule_ids')
    def _compute_pricelist_rule_ids(self):
        for product in self:
            if not product.id:
                product.pricelist_rule_ids = False
                continue
            product.pricelist_rule_ids = product.product_tmpl_id.pricelist_rule_ids.filtered(
                lambda rule: rule.product_id <= product,
            )

    def _inverse_pricelist_rule_ids(self):
        for product in self:
            template = product.product_tmpl_id
            template.pricelist_rule_ids = (
                product.pricelist_rule_ids
                | template.pricelist_rule_ids.filtered(
                    lambda rule: rule.product_id and rule.product_id != product
                )
            )


class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('product_id') and self.env.context.get('default_product_id'):
                vals['product_id'] = self.env.context.get('default_product_id')
            if not vals.get('product_tmpl_id') and self.env.context.get('default_product_tmpl_id'):
                vals['product_tmpl_id'] = self.env.context.get('default_product_tmpl_id')

            if vals.get('product_id'):
                if not vals.get('product_tmpl_id'):
                    product = self.env['product.product'].browse(vals['product_id'])
                    vals['product_tmpl_id'] = product.product_tmpl_id.id
                vals['applied_on'] = '0_product_variant'
            elif vals.get('product_tmpl_id'):
                vals['applied_on'] = '1_product'
        return super().create(vals_list)

    def write(self, vals):
        for item in self:
            product_id = vals.get('product_id', item.product_id.id)
            product_tmpl_id = vals.get('product_tmpl_id', item.product_tmpl_id.id)
            if product_id:
                vals['applied_on'] = '0_product_variant'
                if 'product_tmpl_id' not in vals and not item.product_tmpl_id:
                    product = self.env['product.product'].browse(product_id)
                    vals['product_tmpl_id'] = product.product_tmpl_id.id
            elif product_tmpl_id:
                vals['applied_on'] = '1_product'
        return super().write(vals)

