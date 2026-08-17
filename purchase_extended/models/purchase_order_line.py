from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    product_template_id = fields.Many2one(
        "product.template",
        string="Product",
        compute="_compute_product_template_id",
        readonly=False,
        search="_search_product_template_id",
        domain=[("purchase_ok", "=", True)],
    )
    is_configurable_product = fields.Boolean(
        related="product_template_id.has_configurable_attributes",
        depends=["product_id"],
    )
    product_template_attribute_value_ids = fields.Many2many(
        related="product_id.product_template_attribute_value_ids",
        depends=["product_id"],
    )
    product_no_variant_attribute_value_ids = fields.Many2many(
        "product.template.attribute.value",
        "purchase_order_line_no_variant_rel",
        "purchase_order_line_id",
        "product_template_attribute_value_id",
        string="Extra Values",
        copy=True,
    )

    @api.depends("product_id")
    def _compute_product_template_id(self):
        for line in self:
            line.product_template_id = line.product_id.product_tmpl_id

    def _search_product_template_id(self, operator, value):
        return [("product_id.product_tmpl_id", operator, value)]

    @api.depends(
        "product_id",
        "product_qty",
        "product_uom",
        "company_id",
        "product_no_variant_attribute_value_ids",
    )
    def _compute_price_unit_and_date_planned_and_name(self):
        super()._compute_price_unit_and_date_planned_and_name()

    def _get_product_purchase_description(self, product_lang):
        description = super()._get_product_purchase_description(product_lang)
        values = self.product_no_variant_attribute_value_ids.filtered(
            lambda value: value.product_tmpl_id == self.product_id.product_tmpl_id
        )
        if values:
            description = "\n".join([description, *values.mapped("display_name")])
        return description
