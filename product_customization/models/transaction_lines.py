from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def get_product_multiline_description_sale(self):
        """Keep ``[Reference]`` in the generated sales description."""
        return super(
            ProductProduct,
            self.with_context(show_internal_reference=True),
        ).get_product_multiline_description_sale()


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _get_product_purchase_description(self, product_lang):
        """Keep ``[Reference]`` in the generated purchase description."""
        return super()._get_product_purchase_description(
            product_lang.with_context(show_internal_reference=True)
        )
