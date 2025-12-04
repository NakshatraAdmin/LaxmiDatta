# -*- coding: utf-8 -*-

from odoo import fields, models,api,_


class SalesCommission(models.Model):
    """Creating sales commission model."""
    _name = "sales.commission"
    _description = "Sales Commission"

    name = fields.Char(string="Commission Name", help="Name of the commission", required=True)
    sales_person_ids = fields.Many2many('res.users', string='Sales Person',
                                        help="Sales person")
    commission_type = fields.Selection(
        string="Commission Type",
        selection=[('standard', 'Standard'),
                   ('partner_based', 'Partner Based'),
                   ('product_based', 'Product Based'),
                   ('discount_based', 'Discount Based')
                   ], help="Type of commission")
    std_commission_perc = fields.Float(string='Standard Commission Percentage',
                                       help="Standard commission type")
    affiliated_commission_perc = fields.Float(
        string='Affiliated Partner Commission Percentage',
        help="Affiliated partner commission percentage")
    non_affiliated_commission_perc = fields.Float(
        string='Non-Affiliated Partner Commission Percentage',
        help="Non affiliated commission percentage")
    product_based_ids = fields.One2many(
        "product.based.sales.commission", 'sale_commission_id',
        string='Sales commission Exceptions',
        help="Product based sales commission")
    date = fields.Date(string="Date", help="Date")
    description = fields.Char(string="Description", help="Description")
    commission_amount = fields.Float(string="Commission Amount",
                                     help="Commission amount")

    discount_based_ids = fields.One2many(
        "discount.based.sales.commission", 'sale_commission_id',
        string='Commission Rules', help="Discount based")


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_sales_commission = fields.Boolean(
        string="Enable Sales Commission",
        config_parameter='sales_commission_users.enable_sales_commission',
        implied_group='sales_commission_users.group_sales_commission_access'
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()

        res.update(
            enable_sales_commission = ICPSudo.get_param('sales_commission_users.enable_sales_commission') == 'True'
        )
        return res

    def set_values(self):
        super().set_values()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        group = self.env.ref('sales_commission_users.group_sales_commission_access')

        ICPSudo.set_param(
            'sales_commission_users.enable_sales_commission',
            self.enable_sales_commission
        )

        # 🔥 CUSTOM FIX: APPLY GROUP EXACTLY BASED ON BOOLEAN
        if self.enable_sales_commission:
            group.users = [(4, self.env.uid)]
        else:
            group.users = [(3, self.env.uid)]
