# -*- coding: utf-8 -*-

from odoo import models, fields, api

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    def name_get(self):
        result = []
        for bom in self:
            name = ""
            if bom.code and bom.product_tmpl_id:
                name = f"{bom.code}: [{bom.product_tmpl_id.default_code}] {bom.product_tmpl_id.name}"
            elif bom.code:
                name = bom.code
            elif bom.product_tmpl_id:
                name = bom.product_tmpl_id.name
            else:
                name = "Unnamed BoM"
            result.append((bom.id, name))
        return result


class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    sec_uom_id = fields.Many2one(
        "uom.uom",
        string="Secondary UoM",
        related="product_id.sec_uom_id",
        store=True,
    )
    secondary_product_uom_qty = fields.Float(
        string="Secondary Quantity",
        help="Select the Secondary UoM Quantity",
        store=True,
    )

    consumption_uom_id = fields.Many2one(
        "uom.uom",
        string="Consumption UoM",
        related="product_id.consumption_uom_id",
        store=True,
    )

    consumption_product_uom_qty = fields.Float(
        string="Consumption Quantity",
        help="Select the Consumption UoM Quantity",
        store=True,
    )

    weight = fields.Float(
        string="Weight",
        related="product_id.weight",
        store=True,
        readonly=False,
    )
    height = fields.Float(
        string="Height",
        related="product_id.height",
        store=True,
        readonly=False,
    )
    length = fields.Float(
        string="Length",
        related="product_id.length",
        store=True,
        readonly=False,
    )
    width = fields.Float(
        string="Width",
        related="product_id.width",
        store=True,
        readonly=False,
    )
    depth = fields.Float(
        string="Depth",
        related="product_id.depth",
        store=True,
        readonly=False
    )

    
    @api.depends("product_qty", "product_id.sec_uom_ratio")
    def _compute_secondary_product_uom_qty(self):
        for line in self:
            if line.product_id.is_need_secondary_uom and line.product_qty > 0:
                line.secondary_product_uom_qty = (
                    line.product_id.sec_uom_ratio * line.product_qty
                )
            else:
                line.secondary_product_uom_qty = 0

    def _inverse_secondary_product_uom_qty(self):
        for line in self:
            if line.product_id.is_need_secondary_uom and line.secondary_product_uom_qty > 0:
                if line.product_id.sec_uom_ratio:
                    line.product_qty = (
                        line.secondary_product_uom_qty / line.product_id.sec_uom_ratio
                    )
            else:
                line.product_qty = 0

    @api.onchange('secondary_product_uom_qty')
    def _onchange_secondary_product_uom_qty(self):
        if self.product_id.is_need_secondary_uom and self.secondary_product_uom_qty > 0:
            if self.product_id.sec_uom_ratio:
                self.product_qty = (
                    self.secondary_product_uom_qty / self.product_id.sec_uom_ratio
                )
        else:
            self.product_qty = 0

    @api.onchange('product_id', 'product_qty')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id
            if self.product_id.is_need_secondary_uom:
                self.sec_uom_id = self.product_id.sec_uom_id
                self.product_qty = self.product_qty or 1
                if self.product_qty > 0:
                    self.secondary_product_uom_qty = (
                        self.product_id.sec_uom_ratio * self.product_qty
                    )
                else:
                    self.secondary_product_uom_qty = 0

            if self.product_id.is_need_consumption_uom:
                print("\n" * 30)
                print("Setting consumption UoM and quantity")
                self.consumption_uom_id = self.product_id.consumption_uom_id
                self.product_qty = self.product_qty or 1
                print(self.product_qty)
                print(self.product_id.consumption_uom_ratio)
                if self.product_qty > 0:
                    self.consumption_product_uom_qty = (
                            self.product_id.consumption_uom_ratio * self.product_qty
                    )
                else:
                    self.consumption_product_uom_qty = 0