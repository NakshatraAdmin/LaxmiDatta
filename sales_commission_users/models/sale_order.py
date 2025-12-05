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

        if commission:
            # Standard commission type: a fixed percentage of total amount
            if commission.commission_type == 'standard':
                description = 'Sales Commission - Standard'
                commission_amount = self.amount_total * commission.std_commission_perc / 100

            # Partner-based commission type: check if the partner is affiliated
            elif commission.commission_type == 'partner_based':
                if self.partner_id.affiliated:
                    description = 'Sales Commission - Affiliated Partner'
                    commission_amount = self.amount_total * commission.affiliated_commission_perc / 100
                else:
                    description = 'Sales Commission - Non-Affiliated Partner'
                    commission_amount = self.amount_total * commission.non_affiliated_commission_perc / 100

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
                        commission_amount += self.amount_total * rec.commission / 100

        if description and commission_amount:
            # Split commission amount equally among all selected salespeople
            total_salespersons = len(self.salesperson_ids)
            if total_salespersons > 0:
                split_amount = commission_amount / total_salespersons
                for salesperson in self.salesperson_ids:
                    self.commission_ids = [(0, 0, {
                        'date': self.date_order,
                        'description': description,
                        'sales_person_id': salesperson.id,
                        'order_ref': self.name,
                        'partner_id': self.partner_id.id,
                        'commission': description,
                        'commission_type': commission.commission_type,
                        'commission_amount': split_amount,
                    })]
