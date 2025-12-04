# -*- coding: utf-8 -*-

from odoo import fields, models


class SalesCommissionReport(models.TransientModel):
    """Creating sales commission report model."""
    _name = 'sales.commission.report'
    _description = 'Sales Commission Report'

    sales_person_ids = fields.Many2many('res.users', string='Sales Persons', help="Select multiple sales persons")
    start_date = fields.Date(string='Start Date', help="Start date")
    end_date = fields.Date(string='End Date', help="End date")

    def action_print_report(self):
        """To create a report for sale commission for a sales person"""
        data = {
            'sales_person_ids': [person.id for person in self.sales_person_ids],  # Pass multiple salesperson IDs
            'start_date': self.start_date,
            'end_date': self.end_date,
        }
        return self.env.ref(
            'sales_commission_users.sales_commission_report_action'
        ).report_action(self, data=data)
