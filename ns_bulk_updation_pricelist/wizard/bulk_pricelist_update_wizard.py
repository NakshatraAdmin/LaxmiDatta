# -*- coding: utf-8 -*-

from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, ValidationError


class BulkPricelistUpdateWizard(models.TransientModel):
    _name = 'bulk.pricelist.update.wizard'
    _description = 'Bulk Pricelist Update Wizard'

    pricelist_ids = fields.Many2many(
        'product.pricelist',
        string='Pricelists',
        required=True,
    )
    computation_method = fields.Selection(
        selection=[
            ('percentage', 'Percentage Increase/Decrease'),
            ('fixed_amount', 'Fixed Amount Addition/Subtraction'),
            ('fixed_price', 'Set Fixed Price'),
        ],
        string='Computation Method',
        required=True,
        default='percentage',
    )
    value = fields.Float(
        string='Value / Rate',
        default=0.0,
        help="Percentage value (e.g. 10 for +10%, -5 for -5%), fixed amount (+/-), or direct fixed price.",
    )
    apply_on = fields.Selection(
        selection=[
            ('all_products', 'All Products'),
            ('selected_items', 'Selected Pricelist Items'),
        ],
        string='Apply On',
        required=True,
        default='all_products',
    )
    pricelist_item_ids = fields.Many2many(
        'product.pricelist.item',
        string='Pricelist Items',
    )
    min_quantity = fields.Float(
        string='Minimum Quantity',
        default=1.0,
    )
    date_start = fields.Datetime(
        string='Start Date',
    )
    date_end = fields.Datetime(
        string='End Date',
    )

    @api.model
    def default_get(self, fields_list):
        res = super(BulkPricelistUpdateWizard, self).default_get(fields_list)
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        active_ids = self.env.context.get('active_ids')

        if active_model == 'product.pricelist':
            ids_to_set = active_ids or ([active_id] if active_id else [])
            if ids_to_set:
                res['pricelist_ids'] = [Command.set(ids_to_set)]
        elif active_model == 'product.pricelist.item' and active_ids:
            items = self.env['product.pricelist.item'].browse(active_ids)
            if items:
                pricelists = items.mapped('pricelist_id')
                res['pricelist_ids'] = [Command.set(pricelists.ids)]
                res['apply_on'] = 'selected_items'
                res['pricelist_item_ids'] = [Command.set(items.ids)]
        return res

    @api.onchange('pricelist_ids')
    def _onchange_pricelist_ids(self):
        if self.pricelist_ids and self.pricelist_item_ids:
            filtered_ids = self.pricelist_item_ids.filtered(
                lambda i: i.pricelist_id.id in self.pricelist_ids.ids
            ).ids
            self.pricelist_item_ids = [Command.set(filtered_ids)]

    @api.onchange('apply_on')
    def _onchange_apply_on(self):
        if self.apply_on != 'selected_items':
            self.pricelist_item_ids = [Command.clear()]

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_start and record.date_end and record.date_start > record.date_end:
                raise ValidationError(_("Start Date cannot be after End Date."))

    def _update_item(self, item, product=None):
        """Update existing product.pricelist.item record with proper calculation values."""
        vals = {}
        if self.min_quantity:
            vals['min_quantity'] = self.min_quantity
        if self.date_start:
            vals['date_start'] = self.date_start
        if self.date_end:
            vals['date_end'] = self.date_end

        if self.computation_method == 'fixed_price':
            vals.update({
                'compute_price': 'fixed',
                'fixed_price': max(0.0, self.value),
            })
        elif self.computation_method == 'percentage':
            if item.compute_price == 'percentage':
                vals['percent_price'] = item.percent_price + self.value
            elif item.compute_price == 'fixed':
                new_price = item.fixed_price * (1.0 + (self.value / 100.0))
                vals['fixed_price'] = max(0.0, new_price)
            elif item.compute_price == 'formula':
                if hasattr(item, 'price_discount'):
                    vals['price_discount'] = item.price_discount - self.value
                else:
                    new_price = item.fixed_price * (1.0 + (self.value / 100.0))
                    vals['fixed_price'] = max(0.0, new_price)
            else:
                vals.update({
                    'compute_price': 'percentage',
                    'percent_price': self.value,
                })
        elif self.computation_method == 'fixed_amount':
            if item.compute_price == 'fixed':
                new_price = item.fixed_price + self.value
                vals['fixed_price'] = max(0.0, new_price)
            elif item.compute_price == 'percentage':
                target_prod = product or item.product_id or (item.product_tmpl_id.product_variant_id if item.product_tmpl_id else None)
                base_price = target_prod.lst_price if target_prod else 0.0
                current_price = base_price * (1.0 - (item.percent_price / 100.0)) if base_price else 0.0
                new_price = current_price + self.value
                vals.update({
                    'compute_price': 'fixed',
                    'fixed_price': max(0.0, new_price),
                })
            else:
                new_price = item.fixed_price + self.value
                vals.update({
                    'compute_price': 'fixed',
                    'fixed_price': max(0.0, new_price),
                })

        if vals:
            item.write(vals)

    def _get_new_item_price_vals(self, product=None):
        """Return dict with price computation fields for newly created pricelist item."""
        if self.computation_method == 'fixed_price':
            return {
                'compute_price': 'fixed',
                'fixed_price': max(0.0, self.value),
            }
        elif self.computation_method == 'percentage':
            if product:
                base_price = product.lst_price or 0.0
                calc_price = base_price * (1.0 + (self.value / 100.0))
                return {
                    'compute_price': 'fixed',
                    'fixed_price': max(0.0, calc_price),
                }
            else:
                return {
                    'compute_price': 'percentage',
                    'percent_price': self.value,
                }
        elif self.computation_method == 'fixed_amount':
            if product:
                base_price = product.lst_price or 0.0
                calc_price = base_price + self.value
                return {
                    'compute_price': 'fixed',
                    'fixed_price': max(0.0, calc_price),
                }
            else:
                return {
                    'compute_price': 'fixed',
                    'fixed_price': max(0.0, self.value),
                }
        return {}

    def action_apply_bulk_update(self):
        self.ensure_one()
        if not self.pricelist_ids:
            raise UserError(_("Please select at least one Pricelist."))

        if self.computation_method == 'fixed_price' and self.value < 0:
            raise ValidationError(_("Fixed price cannot be negative."))

        modified_items = self.env['product.pricelist.item']

        if self.apply_on == 'selected_items':
            if not self.pricelist_item_ids:
                raise UserError(_("Please select at least one Pricelist Item."))
            for item in self.pricelist_item_ids:
                self._update_item(item)
                modified_items |= item

        elif self.apply_on == 'all_products':
            for pricelist in self.pricelist_ids:
                items = self.env['product.pricelist.item'].search([
                    ('pricelist_id', '=', pricelist.id),
                ])
                if items:
                    for item in items:
                        self._update_item(item)
                        modified_items |= item
                else:
                    item_vals = {
                        'pricelist_id': pricelist.id,
                        'applied_on': '3_global',
                        'min_quantity': self.min_quantity or 1.0,
                        'date_start': self.date_start,
                        'date_end': self.date_end,
                    }
                    item_vals.update(self._get_new_item_price_vals())
                    new_item = self.env['product.pricelist.item'].create(item_vals)
                    modified_items |= new_item

        return {
            'name': _('Updated Pricelist Items'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.pricelist.item',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', modified_items.ids)],
            'target': 'current',
        }
