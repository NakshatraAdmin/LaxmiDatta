# -*- coding: utf-8 -*-

from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def action_zero_receipt_quantities(self):
        """Set the processed quantity of every receipt operation to zero."""
        receipts = self.filtered(
            lambda picking: picking.picking_type_code == 'incoming'
            and picking.state not in ('done', 'cancel')
        )
        receipts.move_ids.move_line_ids.write({'quantity': 0.0})
        return True
