from odoo import fields, models


class TallyErrorLog(models.Model):
    _name = 'tally.error.log'
    _description = 'Tally Integration Error Log'
    _order = 'date desc, id desc'
    _rec_name = "integration_name"

    date = fields.Datetime(string="Date", default=fields.Datetime.now)
    integration_name = fields.Char(string="Integration Name")
    remark = fields.Char(string="Remark")
    error_log = fields.Text(string="Error Log")
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'tally_error_log_attachment_rel',
        'error_id',
        'attachment_id',
        string="Attachments"
    )
    json_log = fields.Text(string="JSON Log")
