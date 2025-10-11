# -*- coding: utf-8 -*-

from odoo.http import request
from odoo.tools import date_utils

from odoo import models
from odoo import models, fields, api


class CustomQuotation(models.Model):
    _name = 'custom.quotation'
    _description = 'Custom Quotation'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    active = fields.Boolean(string='Active', default=True)
    name = fields.Char(string='Voucher Number', readonly=True, copy=False, tracking=True)
    customer_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    quotation_date = fields.Date(string='Quotation Date', default=fields.Date.today, tracking=True)
    update_date = fields.Datetime(string='Update Date', default=fields.Datetime.now, tracking=True)
    remarks = fields.Char(string='Remarks')
    product_id = fields.Many2one('product.template', string='Product', domain="[('categ_id', '=', product_categ_id)]", tracking=True)
    product_product_id = fields.Many2one('product.product', string='Product', domain="[('categ_id', '=', product_categ_id)]", tracking=True)
    group_product_id = fields.Many2one('product.template', string='Product Name', tracking=True, domain=[('bom_ids', '=', False)])
    cq_item_type_id = fields.Many2one('item.type', string='Item Type')
    cq_sub_product_group_id = fields.Many2one('sub.product.group', string='Sub Product Group')
    product_categ_id = fields.Many2one('product.category', string='Product Category')
    product_uom_id = fields.Many2one('uom.uom', string='Product UOM')
    cq_cost_segment_id = fields.Many2one('cost.segment', string='Cost Segment')
    unit_std_qty = fields.Float(string='Unit Std Qty')
    unit_purchase_rate = fields.Float(string='Unit Purchase Rate')
    consumable_unit_rate = fields.Float(string='Consumable Unit Rate')
    minimum_stock_qty = fields.Float(string='Minimum Stock Qty')
    production_batch_qty = fields.Float(string='Production Batch Qty')
    labour_total_amount = fields.Float(string='Total Labour Cost', compute='_compute_labour_total_amount', store=True)
    bom_total_amount = fields.Float(string='Total Material Cost', compute='_compute_bom_total_amount', store=True)
    direct_overheads = fields.Float(string='Direct Overheads (ON PRIMARY COST)', compute='_compute_direct_overheads', store=True)
    actual_direct_overheads = fields.Float(string='Actual Direct Overheads',compute='_compute_actual_direct_overheads',store=True)
    gross_total = fields.Float(string='Gross Total', compute='_compute_gross_total', store=True)
    indirect_cost = fields.Float(string='Indirect Cost (ON GROSS Total)', compute='_compute_indirect_cost', store=True)
    total_overhead_cost = fields.Float(string='Total Overhead Cost', compute='_compute_total_overhead_cost', store=True)
    net_cost = fields.Float(string='Net Cost', compute='_compute_net_cost', store=True)
    selection_type = fields.Selection([
        ('product', 'By Product (BOM)'),
        ('category', 'By Product Group')
    ], string='Product Selection Type', default=False, tracking=True)
    is_product = fields.Boolean(
        string='Is Product', 
        compute='_compute_selection_type', 
        store=False
    )
    is_category = fields.Boolean(
        string='Is Category', 
        compute='_compute_selection_type', 
        store=False
    )
    cq_sec_uom_id = fields.Many2one(
        "uom.uom",
        string="Secondary UoM",
        help="Select the Secondary UoM",
    )
    cq_ratio = fields.Char(
        string="Ratio",
        help="Ratio of base UoM and the secondary UoM",
    )
    cq_sec_uom_qty = fields.Float(string="Secondary UoM Qty")
    cq_remarks = fields.Char(string="Custom Remarks")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancel', 'Cancel'),
    ], string='Status', default='draft', tracking=True)
    bom_count = fields.Integer(string="BOM Count", compute='_compute_bom_count')
    bom_line_ids = fields.One2many('custom.bom.line', 'quotation_id', string='BOM Lines')
    labour_line_ids = fields.One2many('labour.cost.line', 'line_id', string='Labour Cost Lines')
    profit_material_trading = fields.Float(string='Total Profit - Material Trading', compute='_compute_profit_material_trading', store=True)
    total_profit_trading = fields.Float(string='TOTAL PROFIT TRADING', compute='_compute_total_profit_trading', store=True)
    trading_profit = fields.Float(string='TRADING PROFIT %', compute='_compute_profit_trading', store=True)
    profit_overhead_trading = fields.Float(string='Total Profit Overhead Trading', compute='_compute_profit_overhead_trading', store=True)
    material_cost_trading = fields.Float(string='Material Cost Trading')
    trading_sale_rate = fields.Float(string="Trading Sale Rate", compute="_compute_trading_sale_rate", store=True)
    mrp_trading = fields.Float(string='MRP Trading', compute='_compute_mrp_trading', store=True)
    profit_material_customer = fields.Float(string='Total Profit Material Customer', compute='_compute_profit_material_customer', store=True)
    profit_overhead_customer = fields.Float(string='Total Profit Overhead Customer', compute='_compute_profit_overhead_customer', store=True)
    total_profit_customer = fields.Float(string='TOTAL PROFIT CUSTOMER', compute='_compute_total_profit_customer', store=True)
    customer_profit = fields.Float(string='CUSTOMER PROFIT %', compute='_compute_customer_profit', store=True)
    material_cost_customer = fields.Float(string="Material Cost Customer")
    mrp_customer = fields.Float(string='MRP Customer', compute='_compute_mrp_customer', store=True)
    direct_overhead_cost_percentage = fields.Float(default=0.0)
    indirect_overhead_cost_percentage = fields.Float(default=0.0)
    profit_material_trading_percentage = fields.Float(string='Total Profit - Material Trading (%)', default=0.0)
    profit_material_customer_percentage = fields.Float(string='Total Profit - Material Customer (%)', default=0.0)
    profit_overhead_trading_percentage = fields.Float(string='Total Profit Overhead Trading (%)', default=0.0)
    profit_overhead_customer_percentage = fields.Float(string='Total Profit Overhead Customer (%)', default=0.0)
    customer_sale_rate = fields.Float(string='Customer Sale Rate', compute="_compute_customer_sale_rate", store=True)
    gst_item_gst_rate = fields.Many2many('account.tax', string='GST - Item GST Rate', compute='_compute_gst_item_gst_rate', store=True, relation='custom_quotation_item_tax_rel')
    gst_item_gst_customer_rate = fields.Many2many('account.tax', string='GST - Customer GST Rate', compute='_compute_gst_item_gst_customer_rate', store=True, relation='custom_quotation_customer_tax_rel')
    gst_total_rate_trading = fields.Float(string='GST Total Rate Trading', compute='_compute_gst_total_rate_trading', store=True)
    gst_total_rate_customer = fields.Float(string='GST Total Rate Customer', compute='_compute_gst_total_customer', store=True)
    cq_secondary_uom_ratio = fields.Char(string="Secondary UoM Ratio", help="Secondary UoM ratio from selected product")
    bom_total_amount_cc = fields.Float(string='BOM Total Material Cost', compute='_compute_cc_fields', store=True)
    labour_total_amount_cc = fields.Float(string='Labour Cost Total', compute='_compute_cc_fields', store=True)
    trading_customer_labour_amount = fields.Float(string='Labour Amount Total', compute='_compute_cc_fields', store=True)
    primary_cost = fields.Float(string='Primary Cost', compute="_compute_primary_cost", store=True)
    process_cost = fields.Float(string='Process Cost', compute="_compute_process_cost", store=True)
    profit_material_trading_rs = fields.Float(string="Profit Material Trading Rs.", compute='_compute_profit_material_trading_rs', store=True)
    profit_overhead_trading_rs = fields.Float(string="Profit Overhead Trading Rs.", compute='_compute_profit_overhead_trading_rs', store=True)
    profit_material_customer_rs = fields.Float(string="Profit Material Customer Rs.", compute="_compute_profit_material_customer_rs", store=True)
    profit_overhead_customer_rs = fields.Float(string="Profit Overhead Customer Rs.", compute="_compute_profit_overhead_customer_rs", store=True)
    default_code = fields.Char(string="Internal Reference")


    @api.onchange('product_categ_id')
    def _onchange_product_categ_id(self):
        self.product_product_id = False

    def get_unit_purchase_rate(self):
        self.unit_purchase_rate = self.product_product_id.std_unit_cost
        self.consumable_unit_rate = self.product_product_id.consumable_unit_rate
        for line in self.bom_line_ids:
            line._onchange_product_id()

    @api.depends('labour_total_amount_cc', 'direct_overheads', 'indirect_cost')
    def _compute_process_cost(self):
        for record in self:
            record.process_cost = record.labour_total_amount_cc + record.direct_overheads + record.indirect_cost

    @api.depends('bom_total_amount_cc', 'labour_total_amount_cc')
    def _compute_primary_cost(self):
        for record in self:
            record.primary_cost = record.bom_total_amount_cc + record.labour_total_amount_cc

    @api.depends('bom_total_amount_cc', 'profit_material_trading_percentage')
    def _compute_profit_material_trading_rs(self):
        for record in self:
            record.profit_material_trading_rs = max((record.bom_total_amount_cc * record.profit_material_trading_percentage) / 100, 0.00)

    @api.depends('bom_total_amount_cc', 'profit_material_customer_percentage')
    def _compute_profit_material_customer_rs(self):
        for record in self:
            record.profit_material_customer_rs = max((record.bom_total_amount_cc * record.profit_material_customer_percentage) / 100, 0.0)

    @api.depends('trading_customer_labour_amount', 'profit_overhead_trading_percentage')
    def _compute_profit_overhead_trading_rs(self):
        for record in self:
            record.profit_overhead_trading_rs = max((record.trading_customer_labour_amount * record.profit_overhead_trading_percentage) / 100, 0.00)

    @api.depends('trading_customer_labour_amount', 'profit_overhead_customer_percentage')
    def _compute_profit_overhead_customer_rs(self):
        for record in self:
            record.profit_overhead_customer_rs = max((record.trading_customer_labour_amount * record.profit_overhead_customer_percentage) / 100, 0.00)

    @api.depends('trading_customer_labour_amount', 'profit_overhead_trading_rs')
    def _compute_profit_overhead_trading(self):
        for record in self:
            record.profit_overhead_trading = record.trading_customer_labour_amount + record.profit_overhead_trading_rs

    # @api.onchange('group_product_id')
    # def _onchange_group_product_id(self):
    #     self.cq_item_type_id = False
    #     self.cq_sub_product_group_id = False
    #     self.cq_cost_segment_id = False
    #     self.cq_sec_uom_id = False
    #     self.cq_ratio = False
    #     self.product_uom_id = False
    #     self.cq_secondary_uom_ratio = False
    #     self.product_categ_id = False
    #     self.consumable_unit_rate = 0.0
    #     if self.group_product_id:
    #         self.cq_item_type_id = self.group_product_id.item_type_id.id
    #         self.cq_sub_product_group_id = self.group_product_id.sub_product_group_id.id
    #         self.cq_cost_segment_id = self.group_product_id.cost_segment_id.id
    #         self.cq_sec_uom_id = self.group_product_id.sec_uom_id.id
    #         self.cq_ratio = self.group_product_id.ratio
    #         self.product_uom_id = self.group_product_id.uom_id
    #         self.cq_secondary_uom_ratio = self.group_product_id.sec_uom_ratio
    #         self.product_categ_id = self.group_product_id.categ_id
    #         self.consumable_unit_rate = self.group_product_id.consumable_unit_rate

    @api.depends('bom_total_amount', 'labour_total_amount')
    def _compute_cc_fields(self):
        for record in self:
            record.bom_total_amount_cc = record.bom_total_amount
            record.labour_total_amount_cc = record.labour_total_amount
            record.trading_customer_labour_amount = record.process_cost

    @api.depends('trading_sale_rate', 'gst_item_gst_rate')
    def _compute_gst_total_rate_trading(self):
        for record in self:
            gst_total = sum(record.trading_sale_rate * (tax.amount / 100) for tax in record.gst_item_gst_rate)
            record.gst_total_rate_trading = gst_total

    @api.depends('customer_sale_rate', 'gst_item_gst_customer_rate')
    def _compute_gst_total_customer(self):
        for record in self:
            gst_total_customer = sum(record.customer_sale_rate * (tax.amount / 100) for tax in record.gst_item_gst_customer_rate)
            record.gst_total_rate_customer = gst_total_customer

    @api.depends('profit_material_customer', 'profit_overhead_customer', 'material_cost_customer')
    def _compute_customer_sale_rate(self):
        for record in self:
            record.customer_sale_rate = (
                record.profit_material_customer +
                record.profit_overhead_customer +
                record.material_cost_customer)

    @api.depends('trading_customer_labour_amount', 'profit_overhead_customer_rs')
    def _compute_profit_overhead_customer(self):
        for record in self:
            record.profit_overhead_customer = record.trading_customer_labour_amount + record.profit_overhead_customer_rs

    @api.depends('profit_material_customer_rs', 'profit_overhead_customer_rs')
    def _compute_total_profit_customer(self):
        for record in self:
            record.total_profit_customer = record.profit_material_customer_rs + record.profit_overhead_customer_rs

    @api.depends('profit_material_customer_rs', 'profit_overhead_customer_rs')
    def _compute_customer_profit(self):
        for record in self:
            record.customer_profit = (record.total_profit_customer / record.net_cost) * 100 if record.total_profit_customer and record.net_cost else 0

    @api.depends('bom_total_amount_cc', 'profit_material_customer_rs')
    def _compute_profit_material_customer(self):
        for record in self:
            record.profit_material_customer = record.bom_total_amount_cc + record.profit_material_customer_rs

    @api.depends('customer_sale_rate', 'gst_item_gst_customer_rate')
    def _compute_mrp_customer(self):
        for record in self:
            gst_total = sum(record.customer_sale_rate * (tax.amount / 100) for tax in record.gst_item_gst_customer_rate)
            record.mrp_customer = record.customer_sale_rate + gst_total

    @api.depends('product_product_id')
    def _compute_gst_item_gst_rate(self):
        for record in self:
            if record.product_product_id:
                record.gst_item_gst_rate = [(6, 0, record.product_product_id.taxes_id.ids)]
            else:
                record.gst_item_gst_rate = [(5, 0, 0)]

    @api.depends('product_product_id')
    def _compute_gst_item_gst_customer_rate(self):
        for record in self:
            if record.product_product_id:
                record.gst_item_gst_customer_rate = [(6, 0, record.product_product_id.taxes_id.ids)]
            else:
                record.gst_item_gst_customer_rate = [(5, 0, 0)]

    @api.onchange('profit_overhead_customer_percentage', 'total_overhead_cost')
    def _onchange_profit_overhead_customer_percentage(self):
        if self.profit_overhead_customer_percentage:
            percentage = self.profit_overhead_customer_percentage / 100
            self.profit_overhead_customer = self.total_overhead_cost + (self.total_overhead_cost * percentage)
        else:
            self.profit_overhead_customer = self.total_overhead_cost

    # @api.onchange('profit_material_customer_percentage')
    # def _onchange_profit_material_customer_percentage(self):
    #     self._compute_profit_material_customer()

    @api.onchange('unit_std_qty', 'cq_secondary_uom_ratio')
    def _onchange_calculate_secondary_uom_qty(self):
        for rec in self:
            if rec.unit_std_qty and rec.cq_secondary_uom_ratio:
                try:
                    ratio = float(rec.cq_secondary_uom_ratio)
                    if ratio != 0:
                        rec.cq_sec_uom_qty = rec.unit_std_qty / ratio
                    else:
                        rec.cq_sec_uom_qty = 0.0
                except ValueError:
                    rec.cq_sec_uom_qty = 0.0
            else:
                rec.cq_sec_uom_qty = 0.0

    @api.depends('product_product_id')
    def _compute_gst_item_gst_customer_rate(self):
        for record in self:
            if record.product_product_id:
                record.gst_item_gst_customer_rate = [(6, 0, record.product_product_id.taxes_id.ids)]
            else:
                record.gst_item_gst_customer_rate = [(5, 0, 0)]

    @api.depends('trading_sale_rate', 'gst_item_gst_rate')
    def _compute_mrp_trading(self):
        for record in self:
            gst_total = sum(record.trading_sale_rate * (tax.amount / 100) for tax in record.gst_item_gst_rate)
            record.mrp_trading = record.trading_sale_rate + gst_total

    @api.depends('profit_material_trading', 'profit_overhead_trading', 'material_cost_trading')
    def _compute_trading_sale_rate(self):
        for record in self:
            record.trading_sale_rate = (record.profit_material_trading + record.profit_overhead_trading + record.material_cost_trading)

    @api.depends('gross_total', 'indirect_cost')
    def _compute_net_cost(self):
        for record in self:
            record.net_cost = record.gross_total + record.indirect_cost

    @api.depends('indirect_cost', 'actual_direct_overheads')
    def _compute_total_overhead_cost(self):
        for record in self:
            direct_overheads = record.gross_total * 0.17
            record.total_overhead_cost = direct_overheads + record.indirect_cost

    @api.depends('gross_total', 'indirect_overhead_cost_percentage')
    def _compute_indirect_cost(self):
        for record in self:
            record.indirect_cost = max((record.gross_total * record.indirect_overhead_cost_percentage) / 100, 0.00)

    @api.depends('primary_cost', 'direct_overheads')
    def _compute_gross_total(self):
        for record in self:
            record.gross_total = record.primary_cost + record.direct_overheads

    @api.depends('primary_cost', 'direct_overhead_cost_percentage')
    def _compute_direct_overheads(self):
        for record in self:
            record.direct_overheads = max((record.bom_total_amount_cc * record.direct_overhead_cost_percentage) / 100, 0.00)

    @api.depends('labour_total_amount', 'direct_overheads')
    def _compute_actual_direct_overheads(self):
        for record in self:
            record.actual_direct_overheads = max(record.labour_total_amount, record.direct_overheads)

    @api.depends('labour_line_ids.labour_total_amount')
    def _compute_labour_total_amount(self):
        for record in self:
            total_labour_amount = sum(float(line.labour_total_amount) for line in record.labour_line_ids if line.labour_total_amount)
            record.labour_total_amount = total_labour_amount

    @api.depends('bom_line_ids.amount')
    def _compute_bom_total_amount(self):
        for record in self:
            total_amount = sum(line.amount for line in record.bom_line_ids)
            record.bom_total_amount = total_amount

    @api.depends('product_product_id')
    def _compute_bom_count(self):
        for record in self:
            if record.product_product_id: #change
                record.bom_count = self.env['mrp.bom'].search_count([('product_tmpl_id', '=', record.product_product_id.id)])
            else:
                record.bom_count = 0

    @api.depends('selection_type')
    def _compute_selection_type(self):
        for record in self:
            record.is_product = record.selection_type == 'product'
            record.is_category = record.selection_type == 'category'

    @api.onchange('selection_type')
    def _onchange_selection_type(self):
        if self.selection_type == 'category':
            self.product_product_id = False
            self.bom_line_ids = [(5, 0, 0)]
        elif self.selection_type == 'product':
            self.bom_line_ids = [(5, 0, 0)]
            if self.product_product_id:
                self._onchange_product_id()

    def action_view_bom_record(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'BOMs',
            'view_mode': 'tree,form',
            'res_model': 'mrp.bom',
            'domain': [('product_tmpl_id', '=', self.product_product_id.id)],
            'context': "{'create': False}"
        }

    @api.onchange('bom_total_amount')
    def _onchange_bom_total_amount(self):
        if self.bom_total_amount:
            self.material_cost_trading = self.bom_total_amount
            self.material_cost_customer = self.bom_total_amount 
        else:
            self.material_cost_trading = 0.0
            self.material_cost_customer = 0.0

    @api.onchange('total_overhead_cost')
    def _onchange_total_overhead_cost(self):
        self.profit_overhead_trading = self.total_overhead_cost
        self.profit_overhead_customer = self.total_overhead_cost

    @api.onchange('profit_overhead_trading_percentage', 'total_overhead_cost')
    def _onchange_profit_overhead_trading_percentage(self):
        if self.profit_overhead_trading_percentage and self.profit_overhead_trading_percentage > 0:
            profit = (self.total_overhead_cost * self.profit_overhead_trading_percentage) / 100
            self.profit_overhead_trading = self.total_overhead_cost + profit
        else:
            self.profit_overhead_trading = self.total_overhead_cost

    @api.onchange('produproductt_idct_id')
    def onchange_product_id(self):
        # self.bom_line_ids = [(5, 0, 0)]
        self.cq_item_type_id = False
        self.cq_sub_product_group_id = False
        self.cq_cost_segment_id = False
        self.cq_sec_uom_id = False
        self.cq_ratio = False
        self.product_uom_id = False
        self.cq_secondary_uom_ratio = False
        # self.product_categ_id = False
        if self.product_product_id: #change
            self.cq_item_type_id = self.product_product_id.item_type_id.id
            self.cq_sub_product_group_id = self.product_product_id.sub_product_group_id.id
            self.cq_cost_segment_id = self.product_product_id.cost_segment_id.id
            self.cq_sec_uom_id = self.product_product_id.sec_uom_id.id
            self.cq_ratio = self.product_product_id.ratio
            self.product_uom_id = self.product_product_id.uom_id
            self.cq_secondary_uom_ratio = self.product_product_id.sec_uom_ratio
            self.product_categ_id = self.product_product_id.categ_id
            self.consumable_unit_rate = self.product_product_id.consumable_unit_rate
            self.default_code = self.product_product_id.default_code
            # bom_records = self.env['mrp.bom'].search([('product_tmpl_id', '=', self.product_product_id.id)])
            # for bom in bom_records:
            #     for line in bom.bom_line_ids:
            #         component_product_tmpl = self.env['product.template'].search([
            #             ('name', '=', line.product_id.name)
            #         ], limit=1)
            #         component_product = component_product_tmpl.product_variant_ids[0] if component_product_tmpl.product_variant_ids else None
            #         if component_product:
            #             bom_unit_purchase_rate = component_product.standard_price
            #         else:
            #             bom_unit_purchase_rate = 0.0
            #         sec_qty = line.product_qty * (component_product_tmpl.sec_uom_ratio or 1)
            #         self.bom_line_ids = [(0, 0, {
            #             'quotation_id': self.id,
            #             'component_name': line.product_id.name,
            #             'quantity': line.product_qty,
            #             'sec_qty': sec_qty,
            #             'consume_unit_qty': sec_qty,
            #             'product_cost': line.product_id.standard_price,
            #             'bom_unit_purchase_rate': bom_unit_purchase_rate,
            #         })]
            product_variant = self.product_product_id.product_variant_ids[0] if self.product_product_id.product_variant_ids else None
            if product_variant:
                self.unit_purchase_rate = product_variant.standard_price
            else:
                self.unit_purchase_rate = 0.0
        else:
            self.product_uom_id = False
            self.unit_purchase_rate = 0.0

    @api.onchange('material_cost_trading')
    def _onchange_material_cost_trading(self):
        self.profit_material_trading = self.material_cost_trading
        self.profit_material_customer = self.material_cost_customer

    @api.depends('bom_total_amount_cc', 'profit_material_trading_rs')
    def _compute_profit_material_trading(self):
        for record in self:
            record.profit_material_trading = record.bom_total_amount_cc + record.profit_material_trading_rs

    @api.depends('profit_material_trading_rs', 'profit_overhead_trading_rs')
    def _compute_total_profit_trading(self):
        for record in self:
            record.total_profit_trading = record.profit_material_trading_rs + record.profit_overhead_trading_rs

    @api.depends('total_profit_trading', 'net_cost')
    def _compute_profit_trading(self):
        for record in self:
            record.trading_profit = (record.total_profit_trading / record.net_cost) * 100 if record.total_profit_trading and record.net_cost else 0

    @api.depends('bom_line_ids.amount')
    def _compute_bom_total_amount(self):
        for record in self:
            total_amount = sum(line.amount for line in record.bom_line_ids)
            record.bom_total_amount = total_amount

    # @api.onchange('profit_material_trading_percentage')
    # def _onchange_profit_material_trading_percentage(self):
    #     self._compute_profit_material_trading()

    @api.model_create_multi
    def create(self, vals_list):
        settings = self.env['ir.config_parameter'].sudo()
        for vals in vals_list:
            vals['direct_overhead_cost_percentage'] = settings.get_param('sale.direct_overhead_cost_percentage', default=0.0)
            vals['indirect_overhead_cost_percentage'] = settings.get_param('sale.indirect_overhead_cost_percentage', default=0.0)
            vals['profit_material_trading_percentage'] = settings.get_param('sale.profit_material_trading_percentage', default=0.0)
            vals['profit_overhead_trading_percentage'] = settings.get_param('sale.profit_overhead_trading_percentage', default=0.0)
            vals['profit_material_customer_percentage'] = settings.get_param('sale.profit_material_customer_percentage', default=0.0)
            vals['profit_overhead_customer_percentage'] = settings.get_param('sale.profit_overhead_customer_percentage', default=0.0)

            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('custom.quotation') or 'New'
        return super(CustomQuotation, self).create(vals_list)

    def action_confirm(self):
        for record in self:
            record.state = 'confirmed'

    def action_cancel(self):
        for record in self:
            record.state = 'cancel'

    def action_reset_to_draft(self):
        for record in self:
            record.state = 'draft'

    def print_xlsx_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/custom_quotation/excel_report/%s' % (self.id),
            'target': 'new',
        }
        

class CustomBOMLine(models.Model):
    _name = 'custom.bom.line'
    _description = 'Custom BOM Line'

    quotation_id = fields.Many2one('custom.quotation', string='Order No', required=True)
    product_group = fields.Many2one('product.group', string='Product Group')
    product_categ_id = fields.Many2one('product.category', string='Product Category')
    product_id = fields.Many2one(
        'product.template',
        string='Product',
        domain="[('categ_id', '=', product_categ_id)]",
    )
    product_product_id = fields.Many2one('product.product',
        string='Product',
        domain="[('categ_id', '=', product_categ_id)]",
    )
    component_name = fields.Char(string='Component')
    quantity = fields.Float(string='Unit Std Qty', required=True, default=1)
    bom_unit_purchase_rate = fields.Float(string='Unit Purchase Rate', required=True)
    sec_qty = fields.Float(string='Secondary Quantity')
    product_cost = fields.Float(string='Std Unit Cost')
    consume_unit_rate = fields.Float(string='Consumable Unit Rate')
    consume_unit_qty = fields.Float(string='Consumable Unit Qty')
    amount = fields.Float(string='Amount', compute='_compute_amount', store=True)

    @api.onchange('product_categ_id')
    def _onchange_product_categ_id(self):
        self.product_product_id = False

    @api.onchange('product_product_id')
    def _onchange_product_id(self):
        if self.product_product_id:
            self.bom_unit_purchase_rate = self.product_product_id.standard_price
            self.product_cost = self.product_product_id.std_unit_cost
            self.consume_unit_rate = self.product_product_id.consumable_unit_rate
            self.sec_qty = self.product_product_id.sec_uom_ratio
            self.consume_unit_qty = self.sec_qty

    @api.depends('consume_unit_qty', 'consume_unit_rate')
    def _compute_amount(self):
        for line in self:
            line.amount = line.consume_unit_qty * line.consume_unit_rate

class LabourCLine(models.Model):
    _name = 'labour.cost.line'
    _description = 'Labour Cost Line'

    line_id = fields.Many2one('custom.quotation', string='Order No', required=True)
    labour_cost_id = fields.Many2one(
        'labour.cost', 
        string='Labour Cost', 
        domain="[('category_id', '=', labour_cost_category)]", 
        required=True
    )
    labour_cost_category = fields.Many2one(
        'labour.cost.category', 
        string='Labour Cost Category', 
        required=True
    )
    labour_cost_rate = fields.Float(string='Labour Cost Rate', required=True)
    labour_qty = fields.Float(string='Labour Quantity', required=True, default=1)
    labour_uom = fields.Many2one(
        'uom.uom', 
        string='Labour UOM', 
        required=True, 
        default=lambda self: self.env.ref('uom.product_uom_unit'), 
        readonly=True
    )
    labour_total_amount = fields.Float(string='Labour Total Amount', compute="_compute_labour_total_amount", store=True)

    @api.depends('labour_qty', 'labour_cost_rate')
    def _compute_labour_total_amount(self):
        for line in self:
            line.labour_total_amount = line.labour_qty * line.labour_cost_rate

    @api.onchange('labour_cost_category')
    def _onchange_labour_cost_category(self):
        self.labour_cost_id = False
        self.labour_cost_rate = 0.0

    @api.onchange('labour_cost_id')
    def _onchange_labour_cost_id(self):
        if self.labour_cost_id:
            self.labour_cost_rate = self.labour_cost_id.amount
        else:
            self.labour_cost_rate = 0.0

    @api.onchange('labour_qty', 'labour_cost_rate')
    def _onchange_labour_cost(self):
        for line in self:
            line.labour_total_amount = line.labour_qty * line.labour_cost_rate


class ItemType(models.Model):
    _name = 'item.type'
    _description = 'Item Type'

    name = fields.Char(string='Item Type Name', required=True)


class ProductGroup(models.Model):
    _name = 'product.group'
    _description = 'Product Group'

    name = fields.Char(string='Product Group Name', required=True)


class SubProductGroup(models.Model):
    _name = 'sub.product.group'
    _description = 'Sub Product Group'

    name = fields.Char(string='Sub Product Group Name', required=True)


class CostSegment(models.Model):
    _name = 'cost.segment'
    _description = 'Cost Segment'

    name = fields.Char(string='Cost Segment Name', required=True)


class LabourCost(models.Model):
    _name = 'labour.cost'
    _description = 'Labour Cost'

    name = fields.Char(string='Labour Cost Name', required=True)
    category_id = fields.Many2one(
        comodel_name='labour.cost.category', 
        string='Labour Cost Category',
        required=True
    )
    amount = fields.Float(string='Labour Cost Amount', required=True)


class LabourCostCategory(models.Model):
    _name = 'labour.cost.category'
    _description = 'Labour Cost Category'

    name = fields.Char(string='Labour Cost Category', required=True)