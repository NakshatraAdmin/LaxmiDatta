# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class StockPicking(models.Model):
    _inherit = "stock.picking"

    check_by = fields.Many2one(comodel_name='hr.employee', string='Check By')
    pack_by = fields.Many2one(comodel_name='hr.employee', string='Pack By')
