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
            total = order.amount_total+amount_tax
            # print("====print==",total)
            self.down_payment = downpayment_total
            order.amount_total_after_down_payment = total - downpayment_total


   
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_image = fields.Binary(string="Product Image")
    hsn_sac = fields.Char(string="HSN/SAC" ,related='product_id.l10n_in_hsn_code')

    
    
