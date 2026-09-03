from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    tally_company_name = fields.Char(
        related="company_id.tally_company_name",
        readonly=False,
        string="Company Name",
    )
    tally_company_id = fields.Char(
        related="company_id.tally_company_id",
        readonly=False,
        string="Company ID",
    )
    tally_url = fields.Char(
        related="company_id.tally_url",
        readonly=False,
        string="URL",
    )