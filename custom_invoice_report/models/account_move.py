# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    dispatched_through_id = fields.Char(
        string='Dispatched Through',
        compute='_compute_sale_order_details',
    )
    article_no = fields.Char(
        string='Article No',
        compute='_compute_sale_order_details',
    )
    vehical_num = fields.Char(
        string='VEHICLE NO',
        compute='_compute_sale_order_details',
    )
    other_references = fields.Char(
        string='Other References',
        compute='_compute_sale_order_details',
    )

    def _find_relevant_sale_order(self):
        """Return the order linked through invoice lines, the field, or origin."""
        self.ensure_one()
        sale_order = self.invoice_line_ids.sale_line_ids.order_id[:1] or self.sale_id
        if not sale_order and self.invoice_origin:
            origin_names = [name.strip() for name in self.invoice_origin.split(',') if name.strip()]
            sale_order = self.env['sale.order'].search([('name', 'in', origin_names)], limit=1)
        return sale_order

    @api.depends(
        'sale_id',
        'sale_id.dispatched_through_id',
        'sale_id.article',
        'sale_id.vehicle_no',
        'sale_id.other_references',
        'invoice_line_ids.sale_line_ids.order_id',
        'invoice_origin',
    )
    def _compute_sale_order_details(self):
        for move in self:
            sale_order = move._find_relevant_sale_order()
            move.dispatched_through_id = sale_order.dispatched_through_id if sale_order else False
            move.article_no = sale_order.article if sale_order else False
            move.vehical_num = sale_order.vehicle_no if sale_order else False
            move.other_references = sale_order.other_references if sale_order else False

    @api.onchange('invoice_line_ids', 'invoice_origin')
    def _onchange_set_relevant_sale_order(self):
        for move in self.filtered(lambda record: record.is_invoice(include_receipts=True)):
            sale_order = move._find_relevant_sale_order()
            if sale_order:
                move.sale_id = sale_order

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves.filtered(lambda record: record.is_invoice(include_receipts=True) and not record.sale_id):
            sale_order = move._find_relevant_sale_order()
            if sale_order:
                move.sale_id = sale_order
        return moves
