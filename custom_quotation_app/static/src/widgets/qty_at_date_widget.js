/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";

// Get the QtyAtDatePopover from the registry instead of direct import
const qtyAtDateWidget = registry.category("view_widgets").get("qty_at_date_widget");
const QtyAtDatePopover = qtyAtDateWidget.component.components.Popover;

// Patch the existing QtyAtDatePopover to add warehouse details functionality
patch(QtyAtDatePopover.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.state = useState({
            warehouseDetails: null,
            isLoading: false,
        });
    },

    async loadWarehouseDetails() {
        if (this.state.isLoading) return;

        this.state.isLoading = true;
        try {
            const productId = this.props.record.data.product_id[0];
            const result = await this.orm.call(
                'product.template',
                'get_product_warehouse_details',
                [productId]
            );

            if (result.error) {
                this.state.warehouseDetails = 'Error: ' + result.error;
                this.state.locationDetails = null;
            } else {
                this.state.warehouseDetails = result.warehouse_details || [];
                this.state.locationDetails = result.location_details || [];
            }
        } catch (error) {
            console.error('Error loading warehouse details:', error);
            this.state.warehouseDetails = 'Error loading warehouse details';
            this.state.locationDetails = null;
        } finally {
            this.state.isLoading = false;
        }
    },

    async onShowWarehouseDetails() {
        await this.loadWarehouseDetails();
    }
});