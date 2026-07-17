# -*- coding: utf-8 -*-

from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    salesperson_partner_ids = fields.Many2many(
        'res.partner',
        'account_move_salesperson_partner_rel',
        'move_id',
        'partner_id',
        string='Salespersons',
        domain="[('salesperson_employee_contact', '=', True)]",
        copy=False,
        help='Employee contacts assigned as salespersons for this invoice.',
    )

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
    sale_id =fields.Many2one('sale.order',string="Sale Order")

    dispatched_through_id = fields.Char(related="sale_id.dispatched_through_id", string="Dispatched Through")
    article_no = fields.Char(string="Article No" , related="sale_id.article" )
    vehical_num= fields.Char(string="VEHICLE NO" , related="sale_id.vehicle_no")
    other_references = fields.Char(string = "Other References" , related="sale_id.other_references")

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

    def _sync_invoice_user_from_salesperson_partners(self):
        for move in self:
            move.with_context(skip_salesperson_partner_sync=True).invoice_user_id = move._get_primary_salesperson_user()

    def _sync_salesperson_partners_from_invoice_user(self):
        for move in self:
            move.with_context(skip_salesperson_partner_sync=True).salesperson_partner_ids = move._get_salesperson_partners_from_user(move.invoice_user_id)

    @api.onchange('salesperson_partner_ids')
    def _onchange_salesperson_partner_ids(self):
        for move in self:
            move.invoice_user_id = move._get_primary_salesperson_user()

    @api.onchange('invoice_user_id')
    def _onchange_invoice_user_id_sync_salesperson_partners(self):
        for move in self:
            if move.invoice_user_id and not move.salesperson_partner_ids:
                move.salesperson_partner_ids = move._get_salesperson_partners_from_user(move.invoice_user_id)
            elif not move.invoice_user_id and not move.salesperson_partner_ids:
                move.salesperson_partner_ids = self.env['res.partner']

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        if self.env.context.get('skip_salesperson_partner_sync'):
            return moves

        for move, vals in zip(moves, vals_list):
            if 'salesperson_partner_ids' in vals:
                move._sync_invoice_user_from_salesperson_partners()
            elif 'invoice_user_id' in vals or not move.salesperson_partner_ids:
                move._sync_salesperson_partners_from_invoice_user()
        return moves

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get('skip_salesperson_partner_sync'):
            return res

        if 'salesperson_partner_ids' in vals and 'invoice_user_id' not in vals:
            self._sync_invoice_user_from_salesperson_partners()
        elif 'invoice_user_id' in vals and 'salesperson_partner_ids' not in vals:
            self._sync_salesperson_partners_from_invoice_user()
        return res


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        copy=False,
        index=True,
    )


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
