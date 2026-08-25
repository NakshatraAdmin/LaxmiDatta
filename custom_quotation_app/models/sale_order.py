# -*- coding: utf-8 -*-

import base64

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import image_data_uri

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
