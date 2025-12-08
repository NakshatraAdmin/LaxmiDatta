# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class StockPicking(models.Model):
    _inherit = "stock.picking"

    check_by = fields.Many2one(comodel_name='hr.employee', string='Check By')
    pack_by = fields.Many2one(comodel_name='hr.employee', string='Pack By')
    dispatched_through_id = fields.Many2one('res.partner',string="Dispatched Through" , related="sale_id.dispatched_through_id")
    article_no = fields.Char(string="Article No" , related="sale_id.article" )
    vehical_num= fields.Char(string="VEHICLE NO" , related="sale_id.vehicle_no")
    sale_user_id = fields.Many2one(
        "res.users",
        related="sale_id.user_id",
        string="Salesperson",
        store=True,
        readonly=True,
    )
    bag_no = fields.Char(string="Bag No")

class Stockmove(models.Model):
    _inherit = "stock.move"

    product_image_1920 = fields.Image(
        string='Product Image',
        related='product_id.image_1920',
        readonly=True,
    )
    hsn_sac = fields.Char(string="HSN/SAC" ,related='product_id.l10n_in_hsn_code')
