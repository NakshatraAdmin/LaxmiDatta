# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    previous_price_history_ids = fields.One2many(
        'product.pricelist.history',
        'pricelist_id',
        string="Previous Price History",
        readonly=True,
    )


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

        records = super().create(vals_list)
        records._archive_older_matching_items()
        return records

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

    def _archive_older_matching_items(self):
        """Archive older active price rules for the same pricelist and matching scope
        into product.pricelist.history and remove them from active item_ids."""
        for item in self:
            if not item.pricelist_id:
                continue

            domain = [
                ('pricelist_id', '=', item.pricelist_id.id),
                ('id', '!=', item.id),
            ]

            if item.product_id:
                domain += ['|', ('product_id', '=', item.product_id.id), ('product_tmpl_id', '=', item.product_tmpl_id.id)]
            elif item.product_tmpl_id:
                domain += ['|', ('product_tmpl_id', '=', item.product_tmpl_id.id), ('product_id.product_tmpl_id', '=', item.product_tmpl_id.id)]
            elif item.categ_id:
                domain += [('categ_id', '=', item.categ_id.id)]
            elif item.applied_on == '3_global':
                domain += [('applied_on', '=', '3_global')]

            older_items = self.search(domain)
            if older_items:
                wiz_id = self.env.context.get('active_wizard_id')
                if not wiz_id and hasattr(self.env, 'context') and self.env.context.get('active_model') == 'bulk.pricelist.update.wizard':
                    wiz_id = self.env.context.get('active_id')

                wizard_id_val = wiz_id if (isinstance(wiz_id, int) and wiz_id > 0) else False

                history_vals = []
                for old in older_items:
                    orig_id = old._origin.id if (hasattr(old, '_origin') and old._origin) else old.id
                    h_val = {
                        'pricelist_id': old.pricelist_id.id,
                        'original_item_id': orig_id if isinstance(orig_id, int) else False,
                        'product_id': old.product_id.id if old.product_id else False,
                        'product_tmpl_id': old.product_tmpl_id.id if old.product_tmpl_id else False,
                        'categ_id': old.categ_id.id if old.categ_id else False,
                        'applied_on': old.applied_on,
                        'min_quantity': old.min_quantity,
                        'fixed_price': old.fixed_price,
                        'compute_price': old.compute_price,
                        'percent_price': getattr(old, 'percent_price', 0.0),
                        'price_discount': getattr(old, 'price_discount', 0.0),
                        'price_surcharge': getattr(old, 'price_surcharge', 0.0),
                        'date_start': old.date_start,
                        'date_end': old.date_end,
                        'wizard_id': wizard_id_val,
                    }
                    history_vals.append(h_val)
                if history_vals:
                    self.env['product.pricelist.history'].create(history_vals)
                older_items.unlink()

