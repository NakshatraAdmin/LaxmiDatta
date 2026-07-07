# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

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
    dispatched_through_id = fields.Many2one('res.partner')
    vehicle_no = fields.Char()
    article= fields.Char(string="ARTICLE NO")
    bill_date = fields.Date(string='Due Date', default=fields.Date.today, tracking=True)
    payment_ids = fields.One2many('account.payment', 'sale_order_id', string='Payments')
    payment_count = fields.Integer(compute='_compute_payment_count')

    def _compute_payment_count(self):
        for order in self:
            order.payment_count = len(order.payment_ids)
    
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
