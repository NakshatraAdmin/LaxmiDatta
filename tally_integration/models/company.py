from odoo import _, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    tally_company_name = fields.Char(string="Company Name")
    tally_company_id = fields.Char(string="Company ID")
    tally_url = fields.Char(string="URL")