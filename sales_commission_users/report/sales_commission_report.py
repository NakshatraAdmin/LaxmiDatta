# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SalesCommissionReportAbstract(models.AbstractModel):
    """To create report for sales commission"""
    _name = 'report.sales_commission_users.report_sales_commission'
    _description = 'Sales Commission Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """To get values for the report for sales commission for multiple sales persons"""
        
        # Fetching all salesperson ids from the data passed
        salesperson_ids = data.get('sales_person_ids', [])
        start_date = fields.Date.to_date(data.get('start_date'))
        end_date = fields.Date.to_date(data.get('end_date'))
        
        # Create the domain for filtering commission lines
        domain = []

        # If there are multiple salesperson IDs, filter by them
        if salesperson_ids:
            domain.append(('sales_person_id', 'in', salesperson_ids))

        commission_lines = self.env['commission.lines'].search(domain)
        report_lines = []
        sale_order_cache = {}

        for line in commission_lines:
            sale_order = line.sale_order_id
            if not sale_order and line.order_ref:
                if line.order_ref not in sale_order_cache:
                    sale_order_cache[line.order_ref] = self.env['sale.order'].search(
                        [('name', '=', line.order_ref)], limit=1
                    )
                sale_order = sale_order_cache[line.order_ref]

            source_invoices = sale_order.invoice_ids.filtered(
                lambda move: move.move_type == 'out_invoice'
                and move.state == 'posted'
            ).sorted(lambda move: (move.invoice_date or move.date, move.id))
            total_untaxed = sum(source_invoices.mapped('amount_untaxed'))
            invoices = source_invoices

            if start_date:
                invoices = invoices.filtered(
                    lambda move: (move.invoice_date or move.date)
                    and (move.invoice_date or move.date) >= start_date
                )
            if end_date:
                invoices = invoices.filtered(
                    lambda move: (move.invoice_date or move.date)
                    and (move.invoice_date or move.date) <= end_date
                )

            for invoice in invoices:
                allocated_commission = (
                    line.commission_amount * invoice.amount_untaxed / total_untaxed
                    if total_untaxed else line.commission_amount / len(invoices)
                )
                report_lines.append({
                    'invoice_date': invoice.invoice_date or invoice.date,
                    'invoice_no': invoice.name,
                    'sale_order_no': sale_order.name,
                    'customer_name': invoice.partner_id.name,
                    'untaxed_amount': invoice.amount_untaxed,
                    'commission_percentage': (
                        allocated_commission / invoice.amount_untaxed * 100
                        if invoice.amount_untaxed else 0.0
                    ),
                    'commission_amount': allocated_commission,
                    'currency': invoice.currency_id,
                })

            # Keep legacy lines visible even when their source invoice cannot be
            # resolved (for example, an invoice was deleted after creation).
            if not source_invoices and not start_date and not end_date:
                report_lines.append({
                    'invoice_date': line.date,
                    'invoice_no': '',
                    'sale_order_no': sale_order.name or line.order_ref,
                    'customer_name': line.partner_id.name,
                    'untaxed_amount': 0.0,
                    'commission_percentage': 0.0,
                    'commission_amount': line.commission_amount,
                    'currency': sale_order.currency_id or self.env.company.currency_id,
                })

        return {
            'doc_ids': docids,
            'docs': report_lines,
            'data': data,
        }
        
