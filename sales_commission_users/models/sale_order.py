# -*- coding: utf-8 -*- 

from odoo import fields, models

class SaleOrder(models.Model):
    """Inherits Sale Order model for adding sales commission."""
    _inherit = 'sale.order'

    # Commission type field pointing to the sales.commission model
    commission_type_id = fields.Many2one('sales.commission', string="Commission Type")

    salesperson_ids = fields.Many2many(
        'hr.employee',
        string="Salespersons",
        help="Employees who receive commission for this sale order",
    )

    commission_ids = fields.One2many('commission.lines', 'sale_order_id',
                                     string='Sales Commission',
                                     help="Commission Lines")

    def _create_commission_lines(self):
        """Create commission lines from fully paid customer invoices."""
        self.ensure_one()
        commission_amount = 0.0
        description = ''
        commission = self.commission_type_id
        paid_invoices = self.invoice_ids.filtered(
            lambda invoice: invoice.move_type == 'out_invoice'
            and invoice.state == 'posted'
            and invoice.payment_state == 'paid'
        )
        total_invoiced_amount = sum(paid_invoices.mapped('amount_untaxed'))

        if commission and paid_invoices:
            if commission.commission_type == 'standard':
                description = 'Sales Commission - Standard'
                commission_amount = total_invoiced_amount * commission.std_commission_perc / 100
            elif commission.commission_type == 'partner_based':
                if self.partner_id.affiliated:
                    description = 'Sales Commission - Affiliated Partner'
                    percentage = commission.affiliated_commission_perc
                else:
                    description = 'Sales Commission - Non-Affiliated Partner'
                    percentage = commission.non_affiliated_commission_perc
                commission_amount = total_invoiced_amount * percentage / 100
            elif commission.commission_type == 'product_based':
                for rule in commission.product_based_ids:
                    order_line = self.order_line.filtered(
                        lambda line: line.product_id == rule.product_id
                    )
                    if order_line:
                        description = 'Sales Commission - Product Based (%s)' % order_line.product_id.name
                        commission_amount += rule.product_id.list_price * rule.commission / 100
            elif commission.commission_type == 'discount_based':
                for rule in commission.discount_based_ids:
                    if self.order_line.filtered(lambda line: line.discount >= rule.discount):
                        description = 'Sales Commission - Discount Based'
                        commission_amount += total_invoiced_amount * rule.commission / 100

        commission_lines = []
        total_salespersons = len(self.salesperson_ids)
        if description and commission_amount and total_salespersons:
            split_amount = commission_amount / total_salespersons
            for salesperson in self.salesperson_ids:
                commission_lines.append((0, 0, {
                    'date': self.date_order,
                    'description': description,
                    'sales_person_id': salesperson.id,
                    'order_ref': self.name,
                    'partner_id': self.partner_id.id,
                    'commission_type': commission.commission_type,
                    'commission_amount': split_amount,
                }))
        existing_values = sorted(
            (line.sales_person_id.id, line.description, line.commission_type,
             line.commission_amount)
            for line in self.commission_ids
        )
        new_values = sorted(
            (command[2]['sales_person_id'], command[2]['description'],
             command[2]['commission_type'], command[2]['commission_amount'])
            for command in commission_lines
        )
        if existing_values != new_values:
            # Rebuild only when the paid total changed. Unlinking prevents old
            # lines from becoming orphan records in the commission menu.
            self.commission_ids.unlink()
            self.commission_ids = commission_lines

class AccountMove(models.Model):
    """Generate sales commission after an invoice becomes fully paid."""
    _inherit = 'account.move'
    sale_id = fields.Many2one('sale.order')

    def _compute_payment_state(self):
        """Refresh commissions whenever reconciliation changes payment state."""
        res = super()._compute_payment_state()
        invoices = self.filtered(lambda move: move.move_type == 'out_invoice')
        sale_orders = invoices.invoice_line_ids.sale_line_ids.order_id
        sale_orders |= invoices.sale_id

        # Keep compatibility with invoices linked only through invoice_origin.
        linked_invoices = invoices.filtered(
            lambda move: not move.invoice_line_ids.sale_line_ids.order_id
            and not move.sale_id
            and move.invoice_origin
        )
        if linked_invoices:
            sale_orders |= self.env['sale.order'].search([
                ('name', 'in', linked_invoices.mapped('invoice_origin')),
            ])

        for sale_order in sale_orders.filtered('commission_type_id'):
            sale_order._create_commission_lines()
        return res
