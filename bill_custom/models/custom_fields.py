from odoo import models, fields,api,_

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    other_ref = fields.Char(string="OTHER REFERENCE")
    article= fields.Char(string="ARTICLE NO")
    vehical_num= fields.Char(string="VEHICLE NO")
    less_advance= fields.Char(string="LESS ADVANCE ")
    receivable = fields.Char(string="NET RECEIVABLE RS")


    down_payment = fields.Monetary(
        string="Down Payment",
        currency_field="currency_id",
        help="Amount already received as down payment to be subtracted from the order total."
    )

    amount_total_after_down_payment = fields.Monetary(
        string="Total after Down Payment",
      
        store=True,
        currency_field="currency_id"
    )


    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'order_line.price_total',
             'order_line.is_downpayment', 'currency_id', 'company_id','amount_total')
    def _compute_amounts(self):
        """Compute the total amounts of the SO and compute downpayment-adjusted total.

        - amount_untaxed, amount_tax and amount_total keep their original meanings.
        - x_downpayment_amount = sum of price_total of lines marked is_downpayment (includes tax).
        - x_amount_total_after_downpayment = amount_total - x_downpayment_amount
        """
        for order in self:
            order = order.with_company(order.company_id)
            order_lines = order.order_line.filtered(lambda x: not x.display_type)

            # NORMAL calculation (respects rounding method)
            if order.company_id.tax_calculation_rounding_method == 'round_globally':
                
                # build tax base lines and compute taxes globally
                tax_results = order.env['account.tax']._compute_taxes([
                    line._convert_to_tax_base_line_dict()
                    for line in order_lines
                ])
                totals = tax_results.get('totals', {})
                currency_totals = totals.get(order.currency_id, {}) if totals else {}
                amount_untaxed = currency_totals.get('amount_untaxed', 0.0)
                amount_tax = currency_totals.get('amount_tax', 0.0)
            else:
                # local rounding per line
                # sum price_subtotal for untaxed, and price_tax for taxes
                amount_untaxed = sum(order_lines.mapped('price_subtotal')) or 0.0
                amount_tax = sum(order_lines.mapped('price_tax')) or 0.0
            order.amount_total = order.amount_untaxed + order.amount_tax
            order.amount_untaxed = amount_untaxed
            order.amount_total = order.amount_untaxed + order.amount_tax
           
            down_lines = order.order_line.filtered(lambda l: l.is_downpayment and not l.display_type)
            downpayment_total = sum(down_lines.mapped('price_unit'))
            order.amount_untaxed = amount_untaxed
            order.amount_tax = amount_tax
            order.down_payment = downpayment_total
            af_down = order.amount_total + order.amount_tax
            order.amount_total_after_down_payment = af_down - downpayment_total


    # @api.depends('down_payment', 'amount_total')
    # def _compute_amounts_after_down(self):
    #     print("----",self.amount_total,self.down_payment)
    #     ssssssssss
    #     for order in self:
    #         order.amount_total_after_down_payment = order.amount_total - order.down_payment
            # aaaaaaaaaa
        # ---- Optional: override the official amount_total to subtract downpayment ----
        # If you truly want amount_total to already be reduced by downpayment, uncomment:
        # order.amount_total = (amount_total or 0.0) - downpayment_total


    # @api.depends('amount_total', 'down_payment')
    # def _compute_amounts_after_down(self):
    #     for order in self:
    #         # ensure numeric / avoid None
    #         amt_total = order.amount_total or 0.0
    #         dp = order.down_payment or 0.0
    #         # compute carefully digit-by-digit equivalent (simple subtraction here)
    #         order.amount_total_after_down_payment = amt_total - dp

    # @api.constrains('down_payment')
    # def _check_down_payment_non_negative(self):
    #     for order in self:
    #         if order.down_payment and order.down_payment < 0.0:
    #             raise ValidationError(_("Down payment cannot be negative."))
    #         # optional: prevent down_payment greater than total (if you prefer)
    #         if order.down_payment and order.amount_total is not None:
    #             if order.down_payment > order.amount_total:
    #                 # Decide policy: raise error or allow and show negative remaining.
    #                 # We'll raise an error to keep amounts sensible.
    #                 raise ValidationError(_("Down payment cannot be greater than the order total (%s).") % order.amount_total)

    # @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'order_line.price_total')
    # def _compute_amounts(self):
    #     """Compute the total amounts of the SO."""
    #     for order in self:
    #         order = order.with_company(order.company_id)
    #         order_lines = order.order_line.filtered(lambda x: not x.display_type)

    #         if order.company_id.tax_calculation_rounding_method == 'round_globally':
    #             tax_results = order.env['account.tax']._compute_taxes([
    #                 line._convert_to_tax_base_line_dict()
    #                 for line in order_lines
    #             ])
    #             totals = tax_results['totals']
    #             amount_untaxed = totals.get(order.currency_id, {}).get('amount_untaxed', 0.0)
    #             amount_tax = totals.get(order.currency_id, {}).get('amount_tax', 0.0)
    #         else:
    #             amount_untaxed = sum(order_lines.mapped('price_subtotal'))
    #             amount_tax = sum(order_lines.mapped('price_tax'))

    #         order.amount_untaxed = amount_untaxed
    #         order.amount_tax = amount_tax
    #         order.amount_total = order.amount_untaxed + order.amount_tax


    # @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id','receive_in_advance')
    # def _compute_amount(self):
    #     """Compute the amounts of the SO line."""
    #     for line in self:
    #         price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
    #         if line.product_uom_qty and line.receive_in_advance:
    #             price = price - (line.receive_in_advance/line.product_uom_qty)
    #         taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
    #         line.update({
    #             'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
    #             'price_total': taxes['total_included'],
    #             'price_subtotal': taxes['total_excluded'],
    #         })       

    # @api.depends('order_line.price_subtotal', 'order_line.is_downpayment', 'amount_total', 'currency_id')
    # def _compute_downpayment_totals(self):
    #     for order in self:
    #         # Sum price_subtotal of lines explicitly marked as downpayment
    #         down_amount = sum(line.price_subtotal for line in order.order_line.filtered(lambda l: l.is_downpayment))
    #         # Protect against negative/overflows (optional)
    #         if down_amount < 0:
    #             down_amount = 0.0
    #         if order.amount_total and down_amount > order.amount_total:
    #             down_amount = order.amount_total
    #         order.down_payment = down_amount
    #         order.down_payment = (order.amount_total or 0.0) - down_amount

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_image = fields.Binary(string="Product Image")
    hsn_sac = fields.Char(string="HSN/SAC" ,related='product_id.l10n_in_hsn_code')

    
    
