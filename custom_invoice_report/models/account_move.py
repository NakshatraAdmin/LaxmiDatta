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

    def _get_hsn_tax_details(self):
        """Return one GST summary row per HSN/SAC code for the invoice."""
        self.ensure_one()
        details_by_hsn = {}

        invoice_lines = self.invoice_line_ids.filtered(
            lambda line: line.display_type == 'product' and line.tax_ids
        )
        for line in invoice_lines:
            hsn_code = line.product_id.l10n_in_hsn_code or '-'
            details = details_by_hsn.setdefault(hsn_code, {
                'hsn_code': hsn_code,
                'taxable_value': 0.0,
                'cgst_rate': 0.0,
                'cgst_amount': 0.0,
                'sgst_rate': 0.0,
                'sgst_amount': 0.0,
                'igst_rate': 0.0,
                'igst_amount': 0.0,
                'total_tax_amount': 0.0,
            })

            details['taxable_value'] += line.price_subtotal

            tax_values = line.tax_ids.compute_all(
                line.price_unit * (1.0 - line.discount / 100.0),
                currency=line.currency_id,
                quantity=line.quantity,
                product=line.product_id,
                partner=line.partner_id,
                is_refund=self.move_type in ('out_refund', 'in_refund'),
            )
            for tax_value in tax_values['taxes']:
                tax = self.env['account.tax'].browse(tax_value['id'])
                tax_name = (tax.name or '').upper()
                tax_amount = tax_value['amount']

                if 'IGST' in tax_name:
                    details['igst_rate'] = max(
                        details['igst_rate'], abs(tax.amount)
                    )
                    details['igst_amount'] += tax_amount
                elif 'CGST' in tax_name:
                    details['cgst_rate'] = max(
                        details['cgst_rate'], abs(tax.amount)
                    )
                    details['cgst_amount'] += tax_amount
                elif 'SGST' in tax_name:
                    details['sgst_rate'] = max(
                        details['sgst_rate'], abs(tax.amount)
                    )
                    details['sgst_amount'] += tax_amount
                elif 'GST' in tax_name:
                    # A generic GST tax represents equal CGST and SGST shares.
                    gst_rate = abs(tax.amount) / 2.0
                    details['cgst_rate'] = max(details['cgst_rate'], gst_rate)
                    details['sgst_rate'] = max(details['sgst_rate'], gst_rate)
                    details['cgst_amount'] += tax_amount / 2.0
                    details['sgst_amount'] += tax_amount / 2.0

                details['total_tax_amount'] += tax_amount

        return list(details_by_hsn.values())

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
