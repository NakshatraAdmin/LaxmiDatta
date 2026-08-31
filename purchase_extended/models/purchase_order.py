from odoo import api, fields, models
from odoo.tools import formatLang


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    invoice_cash_rounding_id = fields.Many2one(
        'account.cash.rounding',
        string='Cash Rounding Method',
        default=lambda self: self._get_default_cash_rounding(),
    )

    cash_rounding_amount = fields.Monetary(
        string='Rounding',
        compute='_compute_cash_rounding_amount',
        currency_field='currency_id',
    )

    @api.model
    def _get_default_cash_rounding(self):
        return self.env['account.cash.rounding'].search([
            ('company_id', '=', self.env.company.id),
        ], limit=1)

    @api.depends(
        'amount_untaxed',
        'amount_tax',
        'invoice_cash_rounding_id',
        'currency_id',
    )
    def _compute_cash_rounding_amount(self):
        for order in self:
            rounding = order.invoice_cash_rounding_id

            if rounding:
                order.cash_rounding_amount = rounding.compute_difference(
                    order.currency_id, order.amount_untaxed + order.amount_tax,
                )
            else:
                order.cash_rounding_amount = 0.0

    @api.depends(
        'order_line.price_subtotal',
        'order_line.price_tax',
        'order_line.price_total',
        'invoice_cash_rounding_id',
        'currency_id',
    )
    def _amount_all(self):
        super()._amount_all()

        for order in self:
            rounding = order.invoice_cash_rounding_id
            if rounding:
                base_amount = order.amount_untaxed + order.amount_tax
                order.amount_total = base_amount + rounding.compute_difference(
                    order.currency_id, base_amount,
                )

    @api.depends_context('lang')
    @api.depends(
        'order_line.taxes_id',
        'order_line.price_subtotal',
        'amount_total',
        'amount_untaxed',
        'currency_id',
        'invoice_cash_rounding_id',
        'cash_rounding_amount',
    )
    def _compute_tax_totals(self):
        """Render rounding and the rounded total with Odoo's tax totals widget."""
        super()._compute_tax_totals()
        for order in self:
            if not order.invoice_cash_rounding_id:
                continue

            totals = order.tax_totals
            rounding_amount = order.cash_rounding_amount
            totals['display_rounding'] = True
            if rounding_amount:
                totals['rounding_amount'] = rounding_amount
                totals['formatted_rounding_amount'] = formatLang(
                    self.env, rounding_amount, currency_obj=order.currency_id,
                )
            totals['amount_total'] = order.amount_total
            totals['formatted_amount_total'] = formatLang(
                self.env, order.amount_total, currency_obj=order.currency_id,
            )
