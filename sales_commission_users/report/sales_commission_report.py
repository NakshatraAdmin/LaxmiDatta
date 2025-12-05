# -*- coding: utf-8 -*-

from odoo import api, models


class SalesCommissionReportAbstract(models.AbstractModel):
    """To create report for sales commission"""
    _name = 'report.sales_commission_users.report_sales_commission'
    _description = 'Sales Commission Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """To get values for the report for sales commission for multiple sales persons"""
        
        # Fetching all salesperson ids from the data passed
        salesperson_ids = data.get('sales_person_ids', [])
        
        # Create the domain for filtering commission lines
        domain = []

        # If there are multiple salesperson IDs, filter by them
        if salesperson_ids:
            domain.append(('sales_person_id', 'in', salesperson_ids))

        # Add date filtering if start and end dates are provided
        if data.get('start_date'):
            domain.append(('date', '>=', data['start_date']))
        if data.get('end_date'):
            domain.append(('date', '<=', data['end_date']))

        # Fetch commission lines based on the created domain
        commission_lines = self.env['commission.lines'].search(domain)

        return {
            'doc_ids': docids,
            'docs': commission_lines,
            'data': data,
        }
        
