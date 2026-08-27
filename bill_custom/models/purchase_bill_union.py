from odoo import api, fields, models, tools
from odoo.tools import formatLang


class PurchaseBillUnion(models.Model):
    _inherit = "purchase.bill.union"

    picking_id = fields.Many2one("stock.picking", string="Receipt", readonly=True)

    def init(self):
        """Keep standard posted bills and expose eligible POs once per receipt."""
        tools.drop_view_if_exists(self.env.cr, "purchase_bill_union")
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW purchase_bill_union AS (
                SELECT
                    am.id::bigint AS id,
                    am.name,
                    am.ref AS reference,
                    am.partner_id,
                    am.date,
                    am.amount_untaxed AS amount,
                    am.currency_id,
                    am.company_id,
                    am.id AS vendor_bill_id,
                    NULL::integer AS purchase_order_id,
                    NULL::integer AS picking_id
                FROM account_move am
                WHERE am.move_type = 'in_invoice' AND am.state = 'posted'
            UNION ALL
                SELECT
                    (-1000000000::bigint - sp.id)::bigint AS id,
                    po.name,
                    sp.name AS reference,
                    po.partner_id,
                    sp.date_done::date AS date,
                    0.0 AS amount,
                    po.currency_id,
                    po.company_id,
                    NULL::integer AS vendor_bill_id,
                    po.id AS purchase_order_id,
                    sp.id AS picking_id
                FROM stock_picking sp
                JOIN purchase_order po ON po.id = (
                    SELECT pol.order_id
                    FROM stock_move sm
                    JOIN purchase_order_line pol ON pol.id = sm.purchase_line_id
                    WHERE sm.picking_id = sp.id
                    LIMIT 1
                )
                JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
                WHERE
                    sp.state = 'done'
                    AND spt.code = 'incoming'
                    AND po.state IN ('purchase', 'done')
                    AND po.invoice_status IN ('to invoice', 'no')
                    AND NOT EXISTS (
                        SELECT 1
                        FROM account_move used_bill
                        WHERE used_bill.receipt_id = sp.id
                          AND used_bill.state != 'cancel'
                    )
            )
        """)

    @api.depends("currency_id", "reference", "amount", "purchase_order_id", "picking_id")
    @api.depends_context("show_total_amount")
    def _compute_display_name(self):
        super()._compute_display_name()
        for document in self.filtered("picking_id"):
            amount = 0.0
            for move in document.picking_id.move_ids.filtered(
                lambda stock_move: stock_move.state == "done"
                and stock_move.purchase_line_id
                and not stock_move.scrapped
            ):
                line = move.purchase_line_id
                quantity = move.product_uom._compute_quantity(move.quantity, line.product_uom)
                unit_total = line.price_total / line.product_qty if line.product_qty else line.price_unit
                amount += quantity * unit_total
            document.display_name = "%s - %s: %s" % (
                document.purchase_order_id.name,
                document.picking_id.name,
                formatLang(self.env, amount, monetary=True, currency_obj=document.currency_id),
            )
