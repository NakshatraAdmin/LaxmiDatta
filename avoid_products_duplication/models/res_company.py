from odoo import models,fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    avoid_products_name_duplication = fields.Boolean(
        string='Restrict Products Name Duplication',
        help='If checked, avoid duplicate products names within .'
    )

    avoid_internal_references_duplication = fields.Boolean(
        string='Restrict Products Internal Reference Duplication',
        help='If checked, avoid duplicate products reference within .'
    )
