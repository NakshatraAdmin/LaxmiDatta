# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    down_payment = fields.Monetary(
        string="Down Payment",
        currency_field="currency_id",
        help="Amount already received as down payment to be subtracted from the order total."
    )

    amount_total_after_down_payment = fields.Monetary(
        string="Total after Down Payment",
      
        store=True,
        currency_field="currency_id"
    )

    dispatched_through_id = fields.Many2one('res.partner',string="Dispatched Through")
    article_no = fields.Char(string="Article No")
    vehical_num= fields.Char(string="VEHICLE NO")

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    product_image_1920 = fields.Image(
        string='Product Image',
        related='product_id.image_1920',
        readonly=True,
    )
    sec_uom_id = fields.Many2one(
        "uom.uom",
        string="Secondary UoM",
        related="product_id.sec_uom_id",
        readonly=True,
    )
    secondary_product_uom_qty = fields.Float(
        string="Secondary Quantity",
        help="Secondary UoM Quantity",
        store=True,
    )
    secondary_unit_price = fields.Float(
        string="Secondary Unit Price",
        help="Secondary Unit Price",
        store=True,
    )

    @api.onchange('product_id', 'quantity')
    def _onchange_product_id(self):
        if self.product_id:
            if self.product_id.is_need_secondary_uom:
                self.sec_uom_id = self.product_id.sec_uom_id
                if self.quantity > 0:
                    self.secondary_product_uom_qty = (
                            self.product_id.sec_uom_ratio * self.quantity
                    )
                else:
                    self.secondary_product_uom_qty = 0

    @api.depends('quantity', 'discount', 'price_unit', 'tax_ids', 'currency_id', 'sec_uom_id','secondary_unit_price', 'secondary_product_uom_qty')
    def _compute_totals(self):
        for line in self:
            quantity = line.quantity
            price_unit = line.price_unit

            if line.sec_uom_id and line.secondary_unit_price and line.secondary_product_uom_qty:
                price_unit = line.secondary_unit_price
                quantity = line.secondary_product_uom_qty

            if line.display_type != 'product':
                line.price_total = line.price_subtotal = False
            # Compute 'price_subtotal'.
            line_discount_price_unit = price_unit * (1 - (line.discount / 100.0))
            subtotal = quantity * line_discount_price_unit

            # Compute 'price_total'.
            if line.tax_ids:
                taxes_res = line.tax_ids.compute_all(
                    line_discount_price_unit,
                    quantity=quantity,
                    currency=line.currency_id,
                    product=line.product_id,
                    partner=line.partner_id,
                    is_refund=line.is_refund,
                )
                line.price_subtotal = taxes_res['total_excluded']
                line.price_total = taxes_res['total_included']
            else:
                line.price_total = line.price_subtotal = subtotal

        @api.onchange('secondary_unit_price', 'secondary_product_uom_qty')
        def _onchange_secondary_fields(self):
            self._compute_totals()