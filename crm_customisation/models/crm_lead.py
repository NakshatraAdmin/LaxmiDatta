# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    salesperson_ids = fields.Many2many('hr.employee', string="Salespersons")
