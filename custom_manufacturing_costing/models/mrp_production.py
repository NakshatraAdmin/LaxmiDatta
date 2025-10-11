from odoo import models, fields, api
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    is_no_tracking = fields.Boolean(
        string="No Tracking",
        compute="_compute_is_no_tracking",
        store=False,
        search="_search_is_no_tracking"
    )

    @api.depends('product_id', 'product_id.tracking')
    def _compute_is_no_tracking(self):
        for rec in self:
            rec.is_no_tracking = rec.product_id.tracking == 'none' if rec.product_id else False

    def _search_is_no_tracking(self, operator, value):
        if operator == '=' and value is True:
            return [('product_id.tracking', '=', 'none')]
        elif operator == '=' and value is False:
            return ['|', ('product_id', '=', False), ('product_id.tracking', '!=', 'none')]
        return []