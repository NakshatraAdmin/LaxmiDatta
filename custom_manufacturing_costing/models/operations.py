from odoo import models, fields, api, exceptions, _


class Operations(models.Model):
    _inherit = 'mrp.routing.workcenter'

    process_cost = fields.Float(string="Process Cost")
    no_of_repitation = fields.Integer(string="Nos. of Repitation")
