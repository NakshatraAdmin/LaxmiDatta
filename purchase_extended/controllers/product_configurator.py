from datetime import datetime

from odoo import fields
from odoo.http import Controller, request, route


class PurchaseProductConfiguratorController(Controller):

    @route("/purchase_product_configurator/get_values", type="json", auth="user")
    def get_values(
        self, product_template_id, quantity, currency_id, po_date,
        partner_id, product_uom_id=None, company_id=None, ptav_ids=None,
    ):
        if company_id:
            request.update_context(allowed_company_ids=[company_id])
        template = request.env["product.template"].browse(product_template_id).exists()
        combination = request.env["product.template.attribute.value"]
        if ptav_ids:
            combination = request.env["product.template.attribute.value"].browse(ptav_ids).filtered(
                lambda value: value.product_tmpl_id == template
            )
            missing_lines = (template.attribute_line_ids - combination.attribute_line_id).filtered(
                lambda line: line.attribute_id.display_type != "multi"
            )
            combination += missing_lines.mapped(
                lambda line: line.product_template_value_ids._only_active()[:1]
            )
        if not combination:
            combination = template._get_first_possible_combination()

        return {
            "products": [self._get_product_information(
                template, combination, currency_id, po_date, partner_id,
                quantity, product_uom_id, company_id,
            )],
            "optional_products": [],
        }

    @route("/purchase_product_configurator/update_combination", type="json", auth="user")
    def update_combination(
        self, product_template_id, combination, currency_id, po_date,
        quantity, partner_id, product_uom_id=None, company_id=None,
    ):
        if company_id:
            request.update_context(allowed_company_ids=[company_id])
        template = request.env["product.template"].browse(product_template_id).exists()
        combination = request.env["product.template.attribute.value"].browse(combination)
        product = template._get_variant_for_combination(combination)
        return self._get_basic_information(
            product or template, combination, currency_id, po_date, partner_id,
            quantity, product_uom_id, company_id,
        )

    def _get_product_information(
        self, template, combination, currency_id, po_date, partner_id,
        quantity, product_uom_id, company_id,
    ):
        exclusions = template._get_attribute_exclusions(combination_ids=combination.ids)
        return {
            "product_tmpl_id": template.id,
            **self._get_basic_information(
                template._get_variant_for_combination(combination) or template,
                combination, currency_id, po_date, partner_id, quantity,
                product_uom_id, company_id,
            ),
            "quantity": quantity,
            "attribute_lines": [{
                "id": line.id,
                "attribute": line.attribute_id.read(["id", "name", "display_type"])[0],
                "attribute_values": [{
                    **value.read(["name", "html_color", "image", "is_custom"])[0],
                    "price_extra": 0.0,
                } for value in line.product_template_value_ids
                    if value.ptav_active or value in combination],
                "selected_attribute_value_ids": combination.filtered(
                    lambda value: line in value.attribute_line_id
                ).ids,
                "create_variant": line.attribute_id.create_variant,
            } for line in template.attribute_line_ids],
            "exclusions": exclusions["exclusions"],
            "archived_combinations": exclusions["archived_combinations"],
            "parent_exclusions": exclusions["parent_exclusions"],
            "parent_product_tmpl_ids": [],
        }

    def _get_basic_information(
        self, product_or_template, combination, currency_id, po_date,
        partner_id, quantity, product_uom_id, company_id,
    ):
        info = product_or_template.read(["display_name"])[0]
        info["description_sale"] = product_or_template.description_purchase or False
        if not product_or_template.is_product_variant:
            info["id"] = False
            combination_name = combination._get_combination_name()
            if combination_name:
                info["display_name"] = f'{info["display_name"]} ({combination_name})'
        info["price"] = self._get_purchase_price(
            product_or_template, currency_id, po_date, partner_id,
            quantity, product_uom_id, company_id,
        )
        return info

    def _get_purchase_price(
        self, product_or_template, currency_id, po_date, partner_id,
        quantity, product_uom_id, company_id,
    ):
        product = product_or_template if product_or_template.is_product_variant else product_or_template.product_variant_id
        if not product:
            return 0.0
        company = request.env["res.company"].browse(company_id) or request.env.company
        currency = request.env["res.currency"].browse(currency_id) or company.currency_id
        partner = request.env["res.partner"].browse(partner_id)
        uom = request.env["uom.uom"].browse(product_uom_id) or product.uom_po_id
        date = datetime.fromisoformat(po_date).date() if po_date else fields.Date.today()
        seller = product.with_company(company)._select_seller(
            partner_id=partner,
            quantity=quantity,
            date=date,
            uom_id=uom,
        )
        if seller:
            price = seller.product_uom._compute_price(seller.price, uom)
            return seller.currency_id._convert(price, currency, company, date, round=False)
        price = product.uom_id._compute_price(product.standard_price, uom)
        return product.cost_currency_id._convert(price, currency, company, date, round=False)
