# -*- coding: utf-8 -*-
from odoo import models, fields, api

class MandapDesign(models.Model):
    _name = 'mandap.design'
    _description = 'Mandap Design'
    _order = 'sequence, name'

    name = fields.Char('Design Name', required=True)
    description = fields.Html('Description')
    image = fields.Image('Main Image', max_width=1920, max_height=1920)
    image_ids = fields.One2many('mandap.design.image', 'design_id', 'Images')
    category_id = fields.Many2one('mandap.category', 'Category', required=True)
    price = fields.Float('Starting Price')
    sequence = fields.Integer('Sequence', default=10)
    website_published = fields.Boolean('Published on Website', default=True)
    active = fields.Boolean('Active', default=True)

class MandapDesignImage(models.Model):
    _name = 'mandap.design.image'
    _description = 'Mandap Design Image'

    name = fields.Char('Name')
    image = fields.Image('Image', required=True)
    design_id = fields.Many2one('mandap.design', 'Design', required=True, ondelete='cascade')

class MandapCategory(models.Model):
    _name = 'mandap.category'
    _description = 'Mandap Category'

    name = fields.Char('Category Name', required=True)
    description = fields.Text('Description')
    image = fields.Image('Category Image')
    design_ids = fields.One2many('mandap.design', 'category_id', 'Designs')
    website_published = fields.Boolean('Published on Website', default=True)
