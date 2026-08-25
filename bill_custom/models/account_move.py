from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    receipt_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Receipt",
        copy=False,
        readonly=True,
        help="Select a completed receipt to add only the products and quantities received in it.",
    )

    @api.onchange("purchase_vendor_bill_id", "purchase_id")
    def _onchange_purchase_auto_complete(self):
        """Use the standard autocomplete unless its selected row is a receipt."""
        picking = self.purchase_vendor_bill_id.picking_id
        if not picking:
            return super()._onchange_purchase_auto_complete()

        self.purchase_vendor_bill_id = False
        self.receipt_id = picking
        self._load_receipt_lines(picking)

    def _load_receipt_lines(self, picking):
        purchase = picking.purchase_id
        if not purchase:
            raise ValidationError("The selected receipt is not linked to a purchase order.")

        quantities = defaultdict(float)
        purchase_lines = self.env["purchase.order.line"]
        for move in picking.move_ids.filtered(
            lambda move: move.state == "done" and move.purchase_line_id and not move.scrapped
        ):
            purchase_line = move.purchase_line_id
            quantities[purchase_line] += move.product_uom._compute_quantity(
                move.quantity, purchase_line.product_uom
            )
            purchase_lines |= purchase_line

        if not purchase_lines:
            raise ValidationError("The selected receipt has no completed purchase product moves.")

        invoice_values = purchase.with_company(purchase.company_id)._prepare_invoice()
        has_invoice_lines = bool(self.invoice_line_ids.filtered(
            lambda line: line.display_type not in ("line_note", "line_section")
        ))
        new_currency_id = self.currency_id if has_invoice_lines else invoice_values.get("currency_id")
        invoice_values.pop("ref", None)
        invoice_values.pop("payment_reference", None)
        invoice_values.pop("company_id", None)
        if self.move_type == invoice_values.get("move_type"):
            invoice_values.pop("move_type", None)
        self.update(invoice_values)
        self.currency_id = new_currency_id

        new_lines = self.env["account.move.line"]
        for purchase_line in purchase_lines.sorted(key=lambda line: (line.order_id.id, line.sequence, line.id)):
            values = purchase_line._prepare_account_move_line(self)
            values["quantity"] = quantities[purchase_line]
            new_lines += new_lines.new(values)

        self.invoice_line_ids += new_lines
        origins = set(self.invoice_line_ids.mapped("purchase_line_id.order_id.name"))
        self.invoice_origin = ",".join(origins)
        references = self._get_invoice_reference()
        self.ref = ", ".join(references)
        if not self.payment_reference and references:
            self.payment_reference = references[0] if len(references) == 1 else references[-1]
        if self.company_id != purchase.company_id:
            self.company_id = purchase.company_id

    @api.constrains("receipt_id", "state", "move_type")
    def _check_receipt_billed_once(self):
        for bill in self.filtered(
            lambda move: move.receipt_id
            and move.state != "cancel"
            and move.move_type in ("in_invoice", "in_refund")
        ):
            duplicate = self.search_count([
                ("id", "!=", bill.id),
                ("receipt_id", "=", bill.receipt_id.id),
                ("state", "!=", "cancel"),
                ("move_type", "in", ("in_invoice", "in_refund")),
            ])
            if duplicate:
                raise ValidationError(
                    "Receipt %s is already used on another vendor bill." % bill.receipt_id.name
                )
