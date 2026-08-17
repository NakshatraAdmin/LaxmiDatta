# -*- coding: utf-8 -*-

from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _prepare_invoice(self):
        """Keep the originating order available on the generated invoice."""
        vals = super()._prepare_invoice()
        vals['sale_id'] = self.id
        return vals
