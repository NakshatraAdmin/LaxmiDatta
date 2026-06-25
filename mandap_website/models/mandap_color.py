# -*- coding: utf-8 -*-
from odoo import models, fields

class MandapColor(models.Model):
    _name = 'mandap.color'
    _description = 'Mandap Color'
    _order = 'name'

    name = fields.Char('Color Name', required=True)
    color_code = fields.Char('Color Code', help='Hex color code (e.g., #FF0000 for red)')
    display_color = fields.Char('Display Color', compute='_compute_display_color', store=False)

    def _compute_display_color(self):
        for record in self:
            if record.color_code:
                record.display_color = record.color_code
            else:
                # Default colors based on name
                color_map = {
                    'red': '#FF0000',
                    'gold': '#FFD700',
                    'white': '#FFFFFF',
                    'blue': '#0000FF',
                    'green': '#008000',
                    'purple': '#800080',
                    'pink': '#FFC0CB',
                    'orange': '#FFA500',
                    'yellow': '#FFFF00',
                    'black': '#000000',
                }
                record.display_color = color_map.get(record.name.lower(), '#CCCCCC')
