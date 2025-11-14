# -*- coding: utf-8 -*-


from odoo import models, fields, api

import logging

_logger = logging.getLogger(__name__)


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'
    

    product_template_id = fields.Many2one(
        string="Product Template",
        comodel_name='product.template',
        compute='_compute_product_template_id',
        readonly=False,
        search='_search_product_template_id')

    # x_component_custom_field = fields.Char(string='Component Custom Field')
    # product_no_variant_attribute_value_ids = fields.Many2many(
    #     comodel_name='product.template.attribute.value',
    #     string="Extra Values",
    #     compute='_compute_no_variant_attribute_values',
    #     store=True, readonly=False, precompute=True, ondelete='restrict')

    # product_attribute_ids = fields.Many2many(
    #     'product.template.attribute.value',
    #     string='Attributes',
    #     help='Select attributes for this product variant'
    # )

    # @api.onchange('product_tmpl_id')
    # def _onchange_product_tmpl_id(self):
    #     """Auto reset product_id when changing template"""
    #     for line in self:
    #         line.product_id = False
    #         line.bom_product_template_attribute_value_ids = False

    @api.onchange('bom_product_template_attribute_value_ids')
    def _onchange_product_attribute_ids(self):
        """Find matching variant"""
        for line in self:
            if line.product_tmpl_id and line.bom_product_template_attribute_value_ids:
                domain = [
                    ('product_tmpl_id', '=', line.product_tmpl_id.id),
                    ('bom_product_template_attribute_value_ids', 'in', line.bom_product_template_attribute_value_ids.ids)
                ]
                product = self.env['product.product'].search(domain, limit=1)
                if product:
                    line.product_id = product.id

   

    @api.depends('product_id')
    def _compute_product_template_id(self):
        for line in self:
            line.product_template_id = line.product_id.product_tmpl_id

    def _search_product_template_id(self, operator, value):
        return [('product_id.product_tmpl_id', operator, value)]

    def action_configure_variant(self):
        """Open product configurator popup similar to sale order line"""
        self.ensure_one()
        if not self.product_tmpl_id:
            return {'type': 'ir.actions.act_window_close'}

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.configurator',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_tmpl_id': self.product_tmpl_id.id,
                'no_variant_attributes_price_extra': True,
                'create_product_variant': False,
                'from_bom_line': True,
            }
        }

