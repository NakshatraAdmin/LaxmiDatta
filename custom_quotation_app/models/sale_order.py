# -*- coding: utf-8 -*-

import base64

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import formatLang, image_data_uri

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

    def _auto_init(self):
        self.env.cr.execute("""
            ALTER TABLE sale_order
            DROP CONSTRAINT IF EXISTS sale_order_dispatched_through_id_fkey
        """)
        res = super()._auto_init()
        self.env.cr.execute("""
            UPDATE sale_order so
               SET dispatched_through_id = rp.name
              FROM res_partner rp
             WHERE so.dispatched_through_id ~ '^[0-9]+$'
               AND rp.id = so.dispatched_through_id::integer
        """)
        return res

    salesperson_partner_ids = fields.Many2many(
        'res.partner',
        'sale_order_salesperson_partner_rel',
        'order_id',
        'partner_id',
        string='Salespersons',
        domain="[('salesperson_employee_contact', '=', True)]",
        help='Employee contacts assigned as salespersons for this quotation or order.',
    )
    other_references = fields.Char()
    dispatched_through_id = fields.Char(string="Dispatched Through")
    vehicle_no = fields.Char()
    article= fields.Char(string="ARTICLE NO")
    bill_date = fields.Date(string='Due Date', default=fields.Date.today, tracking=True)
    payment_ids = fields.One2many('account.payment', 'sale_order_id', string='Payments')
    payment_count = fields.Integer(compute='_compute_payment_count')
    advance_payment_amount = fields.Monetary(
        string='Advance Payment',
        compute='_compute_advance_payment_amount',
        store=True,
        currency_field='currency_id',
    )
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
            ('company_id', '=', self.env.company.id)
        ], limit=1)

    @api.depends(
        'amount_untaxed',
        'amount_tax',
        'invoice_cash_rounding_id',
        'invoice_cash_rounding_id.rounding',
        'invoice_cash_rounding_id.rounding_method',
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

    def _compute_payment_count(self):
        for order in self:
            order.payment_count = len(order.payment_ids)

    @api.depends(
        'state',
        'date_order',
        'payment_ids.amount',
        'payment_ids.create_date',
        'payment_ids.currency_id',
        'payment_ids.date',
        'payment_ids.partner_type',
        'payment_ids.payment_type',
        'payment_ids.state',
    )
    def _compute_advance_payment_amount(self):
        invalid_payment_states = ('draft', 'cancel', 'canceled', 'rejected')
        for order in self:
            advance_payment_amount = 0.0
            confirmation_date = order.date_order if order.state not in ('draft', 'sent') else False
            for payment in order.payment_ids:
                if (
                    payment.state in invalid_payment_states
                    or payment.payment_type != 'inbound'
                    or payment.partner_type != 'customer'
                    or (confirmation_date and payment.create_date and payment.create_date > confirmation_date)
                ):
                    continue

                amount = payment.amount
                if payment.currency_id and payment.currency_id != order.currency_id:
                    amount = payment.currency_id._convert(
                        amount,
                        order.currency_id,
                        order.company_id,
                        payment.date or fields.Date.context_today(order),
                    )
                advance_payment_amount += amount
            order.advance_payment_amount = advance_payment_amount

    @api.depends(
        'order_line.price_subtotal',
        'order_line.price_tax',
        'order_line.price_total',
        'invoice_cash_rounding_id',
        'invoice_cash_rounding_id.rounding',
        'invoice_cash_rounding_id.rounding_method',
        'currency_id',
    )
    def _compute_amounts(self):
        """Compute SO totals and apply cash rounding as Odoo does for invoices."""
        for order in self:
            order = order.with_company(order.company_id)
            order_lines = order.order_line.filtered(lambda line: not line.display_type)

            if order.company_id.tax_calculation_rounding_method == 'round_globally':
                tax_results = order.env['account.tax']._compute_taxes([
                    line._convert_to_tax_base_line_dict()
                    for line in order_lines
                ])
                totals = tax_results['totals'].get(order.currency_id, {})
                amount_untaxed = totals.get('amount_untaxed', 0.0)
                amount_tax = totals.get('amount_tax', 0.0)
            else:
                amount_untaxed = sum(order_lines.mapped('price_subtotal'))
                amount_tax = sum(order_lines.mapped('price_tax'))

            order.amount_untaxed = amount_untaxed
            order.amount_tax = amount_tax
            amount_total = amount_untaxed + amount_tax

            rounding = order.invoice_cash_rounding_id
            if rounding:
                amount_total += rounding.compute_difference(
                    order.currency_id, amount_total,
                )
            order.amount_total = amount_total

    @api.depends_context('lang')
    @api.depends(
        'order_line.tax_id',
        'order_line.price_unit',
        'amount_total',
        'amount_untaxed',
        'currency_id',
        'invoice_cash_rounding_id',
        'invoice_cash_rounding_id.rounding',
        'invoice_cash_rounding_id.rounding_method',
        'invoice_cash_rounding_id.strategy',
        'cash_rounding_amount',
    )
    def _compute_tax_totals(self):
        """Provide the same rounding data that the invoice totals widget uses."""
        super()._compute_tax_totals()
        for order in self:
            if not order.invoice_cash_rounding_id:
                continue
            totals = order.tax_totals
            rounding = order.invoice_cash_rounding_id
            rounding_amount = rounding.compute_difference(
                order.currency_id, totals['amount_total'],
            )
            totals['display_rounding'] = True
            if rounding_amount:
                if rounding.strategy == 'add_invoice_line':
                    totals['rounding_amount'] = rounding_amount
                    totals['formatted_rounding_amount'] = formatLang(
                        self.env, rounding_amount, currency_obj=order.currency_id,
                    )
                elif rounding.strategy == 'biggest_tax' and totals['subtotals_order']:
                    max_tax_group = max((
                        tax_group
                        for tax_groups in totals['groups_by_subtotal'].values()
                        for tax_group in tax_groups
                    ), key=lambda tax_group: tax_group['tax_group_amount'])
                    max_tax_group['tax_group_amount'] += rounding_amount
                    max_tax_group['formatted_tax_group_amount'] = formatLang(
                        self.env,
                        max_tax_group['tax_group_amount'],
                        currency_obj=order.currency_id,
                    )

                totals['amount_total'] += rounding_amount
                totals['formatted_amount_total'] = formatLang(
                    self.env, totals['amount_total'], currency_obj=order.currency_id,
                )

    def _get_report_advance_payments(self):
        self.ensure_one()
        invalid_payment_states = ('draft', 'cancel', 'canceled', 'rejected')
        confirmation_date = self.date_order if self.state not in ('draft', 'sent') else False
        return self.payment_ids.filtered(lambda payment: (
            payment.state not in invalid_payment_states
            and payment.payment_type == 'inbound'
            and payment.partner_type == 'customer'
            and not (confirmation_date and payment.create_date and payment.create_date > confirmation_date)
        ))

    def _get_report_signatory_name(self):
        self.ensure_one()
        return self.user_id.name or self.write_uid.name
    
    def _get_salesperson_partners_from_user(self, user):
        self.ensure_one()
        if not user:
            return self.env['res.partner']

        employees = user.sudo().employee_ids
        if self.company_id:
            employees = employees.filtered(lambda emp: emp.company_id == self.company_id)
        return employees.mapped('work_contact_id')

    def _get_primary_salesperson_user(self):
        self.ensure_one()
        employees = self.salesperson_partner_ids.sudo().mapped('employee_ids')
        if self.company_id:
            company_employees = employees.filtered(lambda emp: emp.company_id == self.company_id)
            if company_employees:
                employees = company_employees
        return employees.mapped('user_id')[:1]

    def _sync_user_id_from_salesperson_partners(self):
        for order in self:
            order.with_context(skip_salesperson_partner_sync=True).user_id = order._get_primary_salesperson_user()

    def _sync_salesperson_partners_from_user_id(self):
        for order in self:
            order.with_context(skip_salesperson_partner_sync=True).salesperson_partner_ids = order._get_salesperson_partners_from_user(order.user_id)

    @api.onchange('salesperson_partner_ids')
    def _onchange_salesperson_partner_ids(self):
        for order in self:
            order.user_id = order._get_primary_salesperson_user()

    @api.onchange('user_id')
    def _onchange_user_id_sync_salesperson_partners(self):
        for order in self:
            if order.user_id and not order.salesperson_partner_ids:
                order.salesperson_partner_ids = order._get_salesperson_partners_from_user(order.user_id)
            elif not order.user_id and not order.salesperson_partner_ids:
                order.salesperson_partner_ids = self.env['res.partner']

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        if self.env.context.get('skip_salesperson_partner_sync'):
            return orders

        for order, vals in zip(orders, vals_list):
            if 'salesperson_partner_ids' in vals:
                order._sync_user_id_from_salesperson_partners()
            elif 'user_id' in vals or not order.salesperson_partner_ids:
                order._sync_salesperson_partners_from_user_id()
        return orders

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('skip_salesperson_partner_sync'):
            return res

        if 'salesperson_partner_ids' in vals and 'user_id' not in vals:
            self._sync_user_id_from_salesperson_partners()
        elif 'user_id' in vals and 'salesperson_partner_ids' not in vals:
            self._sync_salesperson_partners_from_user_id()
        return res

    def _prepare_invoice(self):
        vals = super()._prepare_invoice()
        vals['salesperson_partner_ids'] = [fields.Command.set(self.salesperson_partner_ids.ids)]
        if self.invoice_cash_rounding_id:
            vals['invoice_cash_rounding_id'] = self.invoice_cash_rounding_id.id
        else:
            rounding_method = self.env['account.cash.rounding'].search([
                ('company_id', '=', self.company_id.id)
            ], limit=1)

            if rounding_method:
                vals['invoice_cash_rounding_id'] = rounding_method.id

        return vals

    def _generate_qr_code(self, silent_errors=False):
        self.ensure_one()
        if self.company_id.country_code == 'IN' and self.company_id.l10n_in_upi_id:
            payment_url = 'upi://pay?pa=%s&pn=%s&am=%s&tr=%s&tn=%s' % (
                self.company_id.l10n_in_upi_id,
                self.company_id.name,
                self.amount_total,
                self.name,
                ("Payment for %s" % self.name))
            barcode = self.env['ir.actions.report'].barcode(barcode_type="QR", value=payment_url, width=120, height=120)
            return image_data_uri(base64.b64encode(barcode))
        if bank := self.company_id.partner_id.bank_ids[:1]:
            return bank.build_qr_code_base64(self.amount_total, self.name, self.name, self.currency_id, self.partner_id)
        return None

    def action_register_payment(self):
        self.ensure_one()
        if self.state not in ('draft', 'sent'):
            raise UserError(_('You can register a payment only on draft or sent sale orders.'))
        return {
            'name': _('Register Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.register.payment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': self._name,
                'active_id': self.id,
                'default_sale_order_id': self.id,
                'default_amount': self.amount_total,
                'default_communication': self.name,
            },
        }

    def action_view_payments(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('account.action_account_payments')
        action['domain'] = [('sale_order_id', '=', self.id)]
        action['context'] = {
            'default_payment_type': 'inbound',
            'default_partner_type': 'customer',
            'default_partner_id': self.partner_invoice_id.commercial_partner_id.id,
            'default_sale_order_id': self.id,
        }
        return action
