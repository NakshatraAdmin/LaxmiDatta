/** @odoo-module **/

import { serializeDateTime } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { x2ManyCommands } from "@web/core/orm_service";
import { useService } from "@web/core/utils/hooks";
import { SaleOrderLineProductField } from "@sale/js/sale_product_field";
import { ProductConfiguratorDialog } from "@sale_product_configurator/js/product_configurator_dialog/product_configurator_dialog";


class PurchaseProductConfiguratorDialog extends ProductConfiguratorDialog {
    async _loadData() {
        return this.rpc("/purchase_product_configurator/get_values", {
            product_template_id: this.props.productTemplateId,
            quantity: this.props.quantity,
            currency_id: this.props.currencyId,
            po_date: this.props.soDate,
            partner_id: this.props.partnerId,
            product_uom_id: this.props.productUOMId,
            company_id: this.props.companyId,
            ptav_ids: this.props.ptavIds,
        });
    }

    async _updateCombination(product, quantity) {
        return this.rpc("/purchase_product_configurator/update_combination", {
            product_template_id: product.product_tmpl_id,
            combination: this._getCombination(product),
            currency_id: this.props.currencyId,
            po_date: this.props.soDate,
            quantity,
            partner_id: this.props.partnerId,
            product_uom_id: this.props.productUOMId,
            company_id: this.props.companyId,
        });
    }
}

PurchaseProductConfiguratorDialog.props = {
    ...ProductConfiguratorDialog.props,
    partnerId: Number,
};


export class PurchaseOrderLineProductField extends SaleOrderLineProductField {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.orm = useService("orm");
    }

    async _onProductTemplateUpdate() {
        const template = this.props.record.data.product_template_id;
        if (!template) {
            return;
        }
        const result = await this.orm.call(
            "product.template", "get_single_product_variant", [template[0]],
            { context: this.context }
        );
        if (result && result.product_id) {
            await this.props.record.update({
                product_id: [result.product_id, result.product_name],
            });
            return;
        }
        this._openProductConfigurator();
    }

    get isConfigurableTemplate() {
        return Boolean(this.props.record.data.is_configurable_product);
    }

    _editProductConfiguration() {
        this._openProductConfigurator(true);
    }

    async _openProductConfigurator(edit = false) {
        const record = this.props.record;
        const order = record.model.root;
        const ptavIds = record.data.product_template_attribute_value_ids.records.map(
            value => value.resId
        );
        this.dialog.add(PurchaseProductConfiguratorDialog, {
            productTemplateId: record.data.product_template_id[0],
            ptavIds,
            customAttributeValues: [],
            quantity: record.data.product_qty || 1,
            productUOMId: record.data.product_uom?.[0],
            companyId: order.data.company_id[0],
            partnerId: order.data.partner_id[0],
            currencyId: order.data.currency_id[0],
            soDate: serializeDateTime(order.data.date_order),
            edit,
            save: async (product) => {
                const noVariantIds = product.attribute_lines
                    .filter(line => line.create_variant === "no_variant")
                    .flatMap(line => line.selected_attribute_value_ids);
                // Apply the product first so that Odoo can run the purchase-line
                // onchanges (UoM, taxes, vendor, planned date, and discount).
                await record.update({
                    product_id: [product.id, product.display_name],
                    product_no_variant_attribute_value_ids: [x2ManyCommands.set(noVariantIds)],
                });

                // Product onchanges can suggest/reset the quantity and recompute
                // the unit price. Apply the values confirmed in the dialog last.
                await record.update({
                    product_qty: product.quantity,
                    price_unit: product.price,
                });
                order.data.order_line.leaveEditMode();
            },
            discard: () => {
                if (!edit) {
                    order.data.order_line.delete(record);
                }
            },
        });
    }
}

registry.category("fields").add("purchase_product_many2one", {
    ...registry.category("fields").get("sol_product_many2one"),
    component: PurchaseOrderLineProductField,
});
