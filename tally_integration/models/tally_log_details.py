from odoo import fields, models


class TallyLogDetails(models.Model):
    _name = 'tally.log.details'
    _description = 'Tally Log Details'
    _order = 'create_date desc, id desc'
    _rec_name = "integration_name"

    integration_name = fields.Char(string="Integration Name")
    remark = fields.Char(string="Remark")
    count = fields.Integer(string="Count")
    start_date = fields.Datetime(string="Start Date")
    end_date = fields.Datetime(string="End Date")
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'tally_log_details_attachment_rel',
        'log_id',
        'attachment_id',
        string="Attachments"
    )
    json_log = fields.Text(string="JSON Log")
