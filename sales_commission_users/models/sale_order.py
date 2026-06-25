# -*- coding: utf-8 -*- 

from odoo import fields, models, api, _

class SaleOrder(models.Model):
    """Inherits Sale Order model for adding sales commission."""
    _inherit = 'sale.order'

    # Commission type field pointing to the sales.commission model
    commission_type_id = fields.Many2one('sales.commission', string="Commission Type")

    salesperson_ids = fields.Many2many('res.users', string="Salespersons", help="List of Salespeople")

    commission_ids = fields.One2many('commission.lines', 'sale_order_id',
                                     string='Sales Commission',
                                     help="Commission Lines")

    @api.onchange('salesperson_ids', 'commission_type_id')
    def _onchange_salesperson_or_commission_type(self):
        """Automatically creates or updates commission lines when salesperson_ids or commission_type_id is updated."""
        if self.salesperson_ids or self.commission_type_id:
            self._create_commission_lines()

    def action_confirm(self):
        """To add the commission lines in the sale order when it's confirmed."""
        res = super(SaleOrder, self).action_confirm()
        # Ensure that commission type is selected and process commission calculation
        if self.commission_type_id:
            self._create_commission_lines()

        return res

    def _create_commission_lines(self):
        """Handle the creation of commission lines based on the selected commission type."""
        commission_amount = 0.0
        description = ''

        # Retrieve the commission type details from the selected sales.commission record
        commission = self.commission_type_id

        # Get the total invoiced amount (not the sales order amount)
        total_invoiced_amount = sum(invoice.amount_total for invoice in self.invoice_ids)

        if commission:
            # Standard commission type: a fixed percentage of invoiced amount
            if commission.commission_type == 'standard':
                description = 'Sales Commission - Standard'
                commission_amount = total_invoiced_amount * commission.std_commission_perc / 100

            # Partner-based commission type: check if the partner is affiliated
            elif commission.commission_type == 'partner_based':
                if self.partner_id.affiliated:
                    description = 'Sales Commission - Affiliated Partner'
                    commission_amount = total_invoiced_amount * commission.affiliated_commission_perc / 100
                else:
                    description = 'Sales Commission - Non-Affiliated Partner'
                    commission_amount = total_invoiced_amount * commission.non_affiliated_commission_perc / 100

            # Product-based commission type: commission is based on specific products
            elif commission.commission_type == 'product_based':
                for rec in commission.product_based_ids:
                    order_line = self.order_line.filtered(
                        lambda line: line.product_id == rec.product_id
                    )
                    if order_line:
                        description = f'Sales Commission - Product Based ({order_line.product_id.name})'
                        commission_amount += order_line.product_id.list_price * rec.commission / 100

            # Discount-based commission type: applies when discount exceeds a certain percentage
            elif commission.commission_type == 'discount_based':
                for rec in commission.discount_based_ids:
                    order_line = self.order_line.filtered(
                        lambda line: line.discount >= rec.discount
                    )
                    if order_line:
                        description = 'Sales Commission - Discount Based'
                        commission_amount += total_invoiced_amount * rec.commission / 100

        if description and commission_amount:
            # Split commission amount equally among all selected salespeople
            total_salespersons = len(self.salesperson_ids)
            if total_salespersons > 0:
                split_amount = commission_amount / total_salespersons
                commission_lines = []
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
                # Use the 5,0,0 to clear existing commission lines before appending the new ones
                self.commission_ids = [(5, 0, 0)] + commission_lines

class AccountMove(models.Model):
    """Inherits Sale Order model for adding sales commission."""
    _inherit = 'account.move'
    sale_id = fields.Many2one('sale.order')


    def action_post(self):
        """To add the commission lines in the sale order when it's confirmed."""
        res = super(AccountMove, self).action_post()
        sale_order = self.env['sale.order'].search([('name', '=',self.invoice_origin)], limit=1)
        # sale_order = self.env['sale.order'].browse(self.sale_id)
        if sale_order.commission_type_id:
            sale_order._create_commission_lines()
        return res

