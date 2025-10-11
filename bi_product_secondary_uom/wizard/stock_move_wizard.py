# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from odoo.exceptions import UserError


class GenerateQRWizard(models.TransientModel):
    _name = 'generate.qr.wizard'
    _description = 'Generate QR Wizard'

    # stock_move_id = fields.Many2one('stock.move', string="Stock Move", readonly=True)
    # first_lot_number = fields.Char(string="First Lot Number", required=True)
    # quantity_per_lot = fields.Float(string="Quantity per Lot", required=True)
    # quantity_received = fields.Float(string="Quantity Received", required=True)
    # keep_current_lines = fields.Boolean(string="Keep Current Lines")

    # @api.model
    # def default_get(self, fields_list):
    #     res = super(GenerateQRWizard, self).default_get(fields_list)
    #     stock_move_id = self.env.context.get('active_id')
    #     if stock_move_id:
    #         stock_move = self.env['stock.move'].browse(stock_move_id)
    #         res.update({
    #             'stock_move_id': stock_move_id,
    #             'quantity_received': stock_move.product_uom_qty,
    #         })
    #     return res

    # def action_confirm(self):
    #     self.ensure_one()
    #     stock_move = self.stock_move_id
    #     if not self.keep_current_lines:
    #         stock_move.write({'move_line_ids': [(5, 0, 0)]})
    #     existing_quantity = sum(line.quantity for line in stock_move.move_line_ids) if self.keep_current_lines else 0
    #     total_quantity = self.quantity_received - existing_quantity
    #     if total_quantity <= 0:
    #         return {'type': 'ir.actions.act_window_close'}
    #     num_lots = int(total_quantity / self.quantity_per_lot)
    #     remaining_quantity = total_quantity % self.quantity_per_lot
    #     try:
    #         start_lot_number = int(self.first_lot_number)
    #     except ValueError:
    #         raise UserError(_("First Lot Number must be a numeric value."))
    #     for i in range(num_lots):
    #         lot_name = str(start_lot_number + i)
    #         self.env['stock.move.line'].create({
    #             'move_id': stock_move.id,
    #             'product_id': stock_move.product_id.id,
    #             'lot_name': lot_name,
    #             'quantity': self.quantity_per_lot,
    #             'product_uom_id': stock_move.product_uom.id,
    #         })
    #     if remaining_quantity > 0:
    #         lot_name = str(start_lot_number + num_lots)
    #         self.env['stock.move.line'].create({
    #             'move_id': stock_move.id,
    #             'product_id': stock_move.product_id.id,
    #             'lot_name': lot_name,
    #             'quantity': remaining_quantity,
    #             'product_uom_id': stock_move.product_uom.id,
    #         })
    #     return {'type': 'ir.actions.act_window_close'}