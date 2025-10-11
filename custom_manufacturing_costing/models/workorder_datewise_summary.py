from odoo import models, fields


class MrpWorkorderDatewiseSummary(models.TransientModel):
    _name = "mrp.workorder.datewise.summary"
    _description = "Datewise Done and Pending Qty Summary"

    workorder_id = fields.Many2one("mrp.workorder", required=True)
    date = fields.Date(string="Date")
    done_qty = fields.Float(string="Done Qty")
    pending_qty = fields.Float(string="Pending Qty")
