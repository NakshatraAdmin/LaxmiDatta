# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    direct_overhead_cost_percentage = fields.Float(digits=(10, 2), config_parameter='sale.direct_overhead_cost_percentage')
    indirect_overhead_cost_percentage = fields.Float(digits=(10, 2), config_parameter='sale.indirect_overhead_cost_percentage')
    profit_material_trading_percentage = fields.Float(digits=(10, 2), config_parameter='sale.profit_material_trading_percentage')
    profit_overhead_trading_percentage = fields.Float(digits=(10, 2), config_parameter='sale.profit_overhead_trading_percentage')
    profit_material_customer_percentage = fields.Float(digits=(10, 2), config_parameter='sale.profit_material_customer_percentage')
    profit_overhead_customer_percentage = fields.Float(digits=(10, 2), config_parameter='sale.profit_overhead_customer_percentage')
