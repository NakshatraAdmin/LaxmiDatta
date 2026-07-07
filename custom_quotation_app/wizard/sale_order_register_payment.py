# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class SaleOrderRegisterPayment(models.TransientModel):
    _name = 'sale.order.register.payment'
    _description = 'Register Sale Order Payment'
    _check_company_auto = True

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        related='sale_order_id.partner_invoice_id',
        readonly=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='sale_order_id.company_id',
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='sale_order_id.currency_id',
        readonly=True,
    )
    payment_date = fields.Date(
        string='Payment Date',
        required=True,
        default=fields.Date.context_today,
    )
    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True,
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        check_company=True,
        domain="[('id', 'in', available_journal_ids)]",
    )
    available_journal_ids = fields.Many2many(
        'account.journal',
        compute='_compute_available_journal_ids',
    )
    payment_method_line_id = fields.Many2one(
        'account.payment.method.line',
        string='Payment Method',
        required=True,
        domain="[('id', 'in', available_payment_method_line_ids)]",
    )
    available_payment_method_line_ids = fields.Many2many(
        'account.payment.method.line',
        compute='_compute_available_payment_method_line_ids',
    )
    communication = fields.Char(string='Memo')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        order = self.env['sale.order'].browse(self.env.context.get('active_id'))
        if order:
            res.setdefault('sale_order_id', order.id)
            res.setdefault('amount', order.amount_total)
            res.setdefault('communication', order.name)
            journal = self._get_default_journal(order.company_id)
            if journal:
                res.setdefault('journal_id', journal.id)
                payment_method_line = journal._get_available_payment_method_lines('inbound')[:1]
                if payment_method_line:
                    res.setdefault('payment_method_line_id', payment_method_line.id)
        return res

    def _get_default_journal(self, company):
        domain = [('type', 'in', ('bank', 'cash'))]
        if company:
            domain.append(('company_id', '=', company.id))
        journals = self.env['account.journal'].search(domain)
        return journals.filtered('inbound_payment_method_line_ids')[:1]

    @api.depends('company_id')
    def _compute_available_journal_ids(self):
        for wizard in self:
            domain = [('type', 'in', ('bank', 'cash'))]
            if wizard.company_id:
                domain.append(('company_id', '=', wizard.company_id.id))
            journals = self.env['account.journal'].search(domain)
            wizard.available_journal_ids = journals.filtered('inbound_payment_method_line_ids')

    @api.depends('journal_id')
    def _compute_available_payment_method_line_ids(self):
        for wizard in self:
            if wizard.journal_id:
                wizard.available_payment_method_line_ids = wizard.journal_id._get_available_payment_method_lines('inbound')
            else:
                wizard.available_payment_method_line_ids = False

    @api.onchange('available_journal_ids')
    def _onchange_available_journal_ids(self):
        if not self.journal_id and self.available_journal_ids:
            self.journal_id = self.available_journal_ids[0]

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if self.journal_id:
            payment_method_lines = self.journal_id._get_available_payment_method_lines('inbound')
            if self.payment_method_line_id not in payment_method_lines:
                self.payment_method_line_id = payment_method_lines[:1]
        else:
            self.payment_method_line_id = False

    @api.constrains('amount')
    def _check_amount(self):
        for wizard in self:
            if wizard.amount <= 0.0:
                raise ValidationError(_('The payment amount must be greater than zero.'))

    def action_create_payment(self):
        self.ensure_one()
        order = self.sale_order_id
        if order.state not in ('draft', 'sent'):
            raise UserError(_('You can register a payment only on draft or sent sale orders.'))
        if not self.payment_method_line_id:
            raise UserError(_('Please select a payment method.'))

        payment = self.env['account.payment'].create({
            'date': self.payment_date,
            'amount': self.amount,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'ref': self.communication or order.name,
            'journal_id': self.journal_id.id,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.commercial_partner_id.id,
            'payment_method_line_id': self.payment_method_line_id.id,
            'destination_account_id': self.partner_id.with_company(self.company_id).property_account_receivable_id.id,
            'sale_order_id': order.id,
        })
        payment.action_post()
        return {'type': 'ir.actions.act_window_close'}
