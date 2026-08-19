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
            ('category', 'Category'),
            ('products_under_category', 'Products under Category'),
        ],
        string='Apply On',
        required=True,
        default='all_products',
    )
    pricelist_item_ids = fields.Many2many(
        'product.pricelist.item',
        string='Pricelist Items',
    )
    category_ids = fields.Many2many(
        'product.category',
        string='Product Categories',
    )
    category_id = fields.Many2one(
        'product.category',
        string='Category',
    )
    product_line_ids = fields.One2many(
        'bulk.pricelist.update.line',
        'wizard_id',
        string='Product Lines',
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
        if self.apply_on == 'products_under_category' and self.category_id:
            self._update_product_lines()

    @api.onchange('apply_on')
    def _onchange_apply_on(self):
        if self.apply_on != 'selected_items':
            self.pricelist_item_ids = [Command.clear()]
        if self.apply_on != 'category':
            self.category_ids = [Command.clear()]
        if self.apply_on != 'products_under_category':
            self.category_id = False
            self.product_line_ids = [Command.clear()]

    @api.onchange('category_id')
    def _onchange_category_id(self):
        if self.apply_on == 'products_under_category':
            self._update_product_lines()

    def _update_product_lines(self):
        """Helper to populate product_line_ids when category_id or pricelist_ids change."""
        if not self.category_id:
            self.product_line_ids = [Command.clear()]
            return

        products = self.env['product.product'].search([
            ('categ_id', 'child_of', self.category_id.id),
        ])
        lines = []
        pricelist = self.pricelist_ids[0] if self.pricelist_ids else False
        for product in products:
            current_price = 0.0
            if pricelist:
                try:
                    current_price = pricelist._get_product_price(product, 1.0)
                except Exception:
                    current_price = product.lst_price or 0.0
            else:
                current_price = product.lst_price or 0.0

            lines.append(Command.create({
                'product_id': product.id,
                'current_price': current_price,
                'new_price': 0.0,
                'effective_from': self.date_start,
            }))
        self.product_line_ids = [Command.clear()] + lines

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

        if self.apply_on != 'products_under_category' and self.computation_method == 'fixed_price' and self.value < 0:
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

        elif self.apply_on == 'category':
            if not self.category_ids:
                raise UserError(_("Please select at least one category."))

            products = self.env['product.product'].search([
                ('categ_id', 'child_of', self.category_ids.ids),
            ])
            if not products:
                raise UserError(_("No products found in the selected category."))

            existing_items = self.env['product.pricelist.item'].search([
                ('pricelist_id', 'in', self.pricelist_ids.ids),
            ])
            item_map = {}
            tmpl_item_map = {}
            for item in existing_items:
                if item.product_id:
                    item_map[(item.pricelist_id.id, item.product_id.id)] = item
                elif item.product_tmpl_id:
                    tmpl_item_map[(item.pricelist_id.id, item.product_tmpl_id.id)] = item

            new_items_vals = []
            for pricelist in self.pricelist_ids:
                for product in products:
                    existing_item = item_map.get((pricelist.id, product.id)) or tmpl_item_map.get((pricelist.id, product.product_tmpl_id.id))
                    if existing_item:
                        self._update_item(existing_item, product=product)
                        modified_items |= existing_item
                    else:
                        item_vals = {
                            'pricelist_id': pricelist.id,
                            'product_id': product.id,
                            'product_tmpl_id': product.product_tmpl_id.id,
                            'applied_on': '0_product_variant',
                            'min_quantity': self.min_quantity or 1.0,
                            'date_start': self.date_start,
                            'date_end': self.date_end,
                        }
                        item_vals.update(self._get_new_item_price_vals(product=product))
                        new_items_vals.append(item_vals)

            if new_items_vals:
                created_items = self.env['product.pricelist.item'].create(new_items_vals)
                modified_items |= created_items

        elif self.apply_on == 'products_under_category':
            if not self.category_id:
                raise UserError(_("Please select a category."))

            if not self.product_line_ids:
                raise UserError(_("No products found in the selected category."))

            edited_lines = self.product_line_ids.filtered(lambda l: l.new_price > 0)
            if not edited_lines:
                raise UserError(_("Please enter at least one new price."))

            for line in self.product_line_ids:
                if line.new_price < 0:
                    raise ValidationError(_("New Price cannot be negative."))

            existing_items = self.env['product.pricelist.item'].search([
                ('pricelist_id', 'in', self.pricelist_ids.ids),
            ])
            item_map = {}
            tmpl_item_map = {}
            for item in existing_items:
                if item.product_id:
                    item_map[(item.pricelist_id.id, item.product_id.id)] = item
                elif item.product_tmpl_id:
                    tmpl_item_map[(item.pricelist_id.id, item.product_tmpl_id.id)] = item

            new_items_vals = []
            for line in edited_lines:
                product = line.product_id
                start_date = line.effective_from or self.date_start
                for pricelist in self.pricelist_ids:
                    existing_item = item_map.get((pricelist.id, product.id)) or tmpl_item_map.get((pricelist.id, product.product_tmpl_id.id))
                    if existing_item:
                        vals = {
                            'compute_price': 'fixed',
                            'fixed_price': line.new_price,
                            'min_quantity': self.min_quantity or 1.0,
                        }
                        if start_date:
                            vals['date_start'] = start_date
                        if self.date_end:
                            vals['date_end'] = self.date_end
                        existing_item.write(vals)
                        modified_items |= existing_item
                    else:
                        item_vals = {
                            'pricelist_id': pricelist.id,
                            'product_id': product.id,
                            'product_tmpl_id': product.product_tmpl_id.id,
                            'applied_on': '0_product_variant',
                            'compute_price': 'fixed',
                            'fixed_price': line.new_price,
                            'min_quantity': self.min_quantity or 1.0,
                            'date_start': start_date,
                            'date_end': self.date_end,
                        }
                        new_items_vals.append(item_vals)

            if new_items_vals:
                created_items = self.env['product.pricelist.item'].create(new_items_vals)
                modified_items |= created_items

        return {
            'name': _('Updated Pricelist Items'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.pricelist.item',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', modified_items.ids)],
            'target': 'current',
        }


class BulkPricelistUpdateLine(models.TransientModel):
    _name = 'bulk.pricelist.update.line'
    _description = 'Bulk Pricelist Update Line'

    wizard_id = fields.Many2one(
        'bulk.pricelist.update.wizard',
        string='Wizard',
        ondelete='cascade',
        required=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        readonly=True,
    )
    current_price = fields.Float(
        string='Current Price',
        readonly=True,
    )
    new_price = fields.Float(
        string='New Price',
        default=0.0,
    )
    price_difference = fields.Float(
        string='Price Difference',
        compute='_compute_price_difference',
        readonly=True,
    )
    effective_from = fields.Datetime(
        string='Effective From',
    )

    @api.depends('new_price', 'current_price')
    def _compute_price_difference(self):
        for line in self:
            if line.new_price:
                line.price_difference = line.new_price - line.current_price
            else:
                line.price_difference = 0.0
