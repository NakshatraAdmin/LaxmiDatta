# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _
from odoo.exceptions import ValidationError, UserError
from collections import Counter
from odoo.tools.float_utils import float_compare

class StockAssignSerial(models.TransientModel):
    _inherit = 'stock.assign.serial'

    def apply(self):
        result = super(StockAssignSerial, self).apply()
        if self.production_id:
            backorder_count = self.production_id.mrp_production_backorder_count
            is_current_backorder = False
            if self.production_id.procurement_group_id:
                all_productions = self.production_id.procurement_group_id.mrp_production_ids
                if len(all_productions) > 1:
                    sorted_productions = all_productions.sorted('create_date')
                    if self.production_id != sorted_productions[0]:
                        is_current_backorder = True
                        backorder_count += 1
            if backorder_count > 0:
                if self.production_id.procurement_group_id:
                    all_productions = self.production_id.procurement_group_id.mrp_production_ids
                    if is_current_backorder:
                        backorders = all_productions - all_productions.sorted('create_date')[0]
                    else:
                        backorders = all_productions - self.production_id
                else:
                    backorders = self.env['mrp.production']
                if self.production_id.workorder_ids:
                    for workorder in self.production_id.workorder_ids:
                        new_total_operation = workorder.no_of_repitation * backorder_count
                        workorder.total_operation = new_total_operation
                        workorder._compute_done_and_pending()
                for backorder in backorders:
                    for workorder in backorder.workorder_ids:
                        workorder.total_operation = 0
                        workorder._compute_done_and_pending()
        print("=== Finished stock.assign.serial apply method ===")
        return result

    def _assign_serial_numbers(self, cancel_remaining_quantity=False):
        serial_numbers = self._get_serial_numbers()
        # self._reset_production_qties()
        productions = self.production_id._split_productions(
            {self.production_id: [1] * len(serial_numbers)}, cancel_remaining_quantity, set_consumed_qty=True)
        production_lots_vals = []
        for serial_name in serial_numbers:
            production_lots_vals.append({
                'product_id': self.production_id.product_id.id,
                'company_id': self.production_id.company_id.id,
                'name': serial_name,
            })
        production_lots = self.env['stock.lot'].create(production_lots_vals)
        for production, production_lot in zip(productions, production_lots):
            production.lot_producing_id = production_lot.id
            production.qty_producing = production.product_qty
            for workorder in production.workorder_ids:
                workorder.qty_produced = workorder.qty_producing

        if self.mark_as_done:
            productions.button_mark_done()