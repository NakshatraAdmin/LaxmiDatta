import logging

from odoo import api, models


_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.depends("name", "default_code", "product_tmpl_id")
    @api.depends_context(
        "display_default_code",
        "seller_id",
        "company_id",
        "partner_id",
        "use_partner_name",
    )
    def _compute_display_name(self):
        # Hide internal references without changing product search behavior.
        display_reference = self.env.context.get("show_internal_reference", False)
        products_without_reference = self.with_context(
            display_default_code=display_reference
        )
        super(ProductProduct, products_without_reference)._compute_display_name()
        for product, product_without_reference in zip(
            self, products_without_reference
        ):
            product.display_name = product_without_reference.display_name

    @api.depends_context("partner_id", "show_internal_reference")
    def _compute_partner_ref(self):
        """Keep the traditional reference in generated line descriptions."""
        products_with_reference = self.with_context(show_internal_reference=True)
        super(ProductProduct, products_with_reference)._compute_partner_ref()
        for product, product_with_reference in zip(self, products_with_reference):
            product.partner_ref = product_with_reference.partner_ref

    @api.model
    def cron_update_product_cost_from_bom(self):
        bom_products = self.env["mrp.bom"].search([
            ("product_id", "!=", False),
        ]).mapped("product_id")

        for product in bom_products:
            try:
                product.button_bom_cost()
            except Exception as error:
                _logger.warning(
                    "Failed to update cost for product %s: %s",
                    product.display_name,
                    error,
                )


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.depends("name", "default_code")
    def _compute_display_name(self):
        """Display template names without ``[Internal Reference]``."""
        for template in self:
            template.display_name = template.name or False
