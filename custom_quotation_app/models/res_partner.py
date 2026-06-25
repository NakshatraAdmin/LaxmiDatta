# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.osv import expression


class ResPartner(models.Model):
    _inherit = 'res.partner'

    salesperson_employee_contact = fields.Boolean(
        string='Employee Salesperson Contact',
        compute='_compute_salesperson_employee_contact',
        search='_search_salesperson_employee_contact',
    )

    def _compute_salesperson_employee_contact(self):
        employee_contact_ids = set(
            self.env['hr.employee'].sudo().search([
                ('work_contact_id', 'in', self.ids),
            ]).mapped('work_contact_id').ids
        )
        for partner in self:
            partner.salesperson_employee_contact = partner.id in employee_contact_ids

    def _search_salesperson_employee_contact(self, operator, value):
        employee_contact_ids = self.env['hr.employee'].sudo().search([
            ('work_contact_id', '!=', False),
        ]).mapped('work_contact_id').ids

        if operator not in ('=', '!='):
            return [('id', 'in', employee_contact_ids)] if value else [('id', 'not in', employee_contact_ids)]

        use_in_operator = (operator == '=' and bool(value)) or (operator == '!=' and not bool(value))
        return [('id', 'in' if use_in_operator else 'not in', employee_contact_ids)]

    @api.model
    def _name_search(self, name="", args=None, operator="ilike", limit=100, order=None):
        args = args or []

        domain = []
        if name:
            domain = [
                "|", "|", "|",
                ("name", operator, name),
                ("mobile", operator, name),
                ("phone", operator, name),
                ("email", operator, name),
            ]

        return self._search(
            expression.AND([domain, args]),
            limit=limit,
            order=order,
        )

    def name_get(self):
        result = []
        for partner in self:
            name = partner.name or ""
            if partner.mobile:
                name = f"{name} [{partner.mobile}]"
            result.append((partner.id, name))
        return result
