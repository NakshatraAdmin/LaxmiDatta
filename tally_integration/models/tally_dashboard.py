import traceback
from odoo import _, fields, models
from odoo.exceptions import ValidationError


class TallyDashboard(models.Model):
    _name = 'tally.dashboard'
    _description = 'Tally Integration Dashboard'

    name = fields.Char(string="Integration Name", required=True)
    code = fields.Char(string="Code", required=True)
    sequence = fields.Integer(string="Sequence", default=10)
    active = fields.Boolean(string="Active", default=True)

    def action_push_uom_to_tally(self):
        self.ensure_one()
        company = self.env.company

        # Step 1: Validate Tally configuration using explicit if checks
        if not company.tally_company_name or not company.tally_company_id or not company.tally_url:
            raise ValidationError(_(
                "Please configure Tally Company Name, Company ID and URL before starting the integration."
            ))

        start_date = fields.Datetime.now()

        # Step 2: Find all UOM records where is_tally is False
        uom_records = self.env['uom.uom'].search([('is_tally', '=', False)])

        if not uom_records:
            end_date = fields.Datetime.now()
            log_record = self.env['tally.log.details'].create({
                'integration_name': 'UOM Integration',
                'remark': 'All UOM records are already integrated in Tally.',
                'count': 0,
                'start_date': start_date,
                'end_date': end_date,
                'json_log': 'No pending UOM records found.',
            })
            return {
                'name': _('Log Details'),
                'type': 'ir.actions.act_window',
                'res_model': 'tally.log.details',
                'res_id': log_record.id,
                'view_mode': 'form',
                'target': 'current',
            }

        # Step 3, 4, 5: Call action_send_to_tally and process result / error
        try:
            res = uom_records.action_send_to_tally()

            # Mark processed UOMs as integrated
            uom_records.write({'is_tally': True})

            end_date = fields.Datetime.now()
            attachment = res.get('attachment') if isinstance(res, dict) else False
            xml_content = res.get('xml_content') if isinstance(res, dict) else ''
            response_obj = res.get('response') if isinstance(res, dict) else None
            response_text = response_obj.text if response_obj and hasattr(response_obj, 'text') else str(response_obj or '')

            log_payload = f"Request XML:\n{xml_content}\n\nResponse:\n{response_text}"

            log_record = self.env['tally.log.details'].create({
                'integration_name': 'UOM Integration',
                'remark': f'Created {len(uom_records)} UOM in Tally',
                'count': len(uom_records),
                'start_date': start_date,
                'end_date': end_date,
                'attachment_ids': [(6, 0, [attachment.id])] if attachment else [(6, 0, [])],
                'json_log': log_payload,
            })

            return {
                'name': _('Log Details'),
                'type': 'ir.actions.act_window',
                'res_model': 'tally.log.details',
                'res_id': log_record.id,
                'view_mode': 'form',
                'target': 'current',
            }
        except ValidationError:
            raise
        except Exception as e:
            error_trace = traceback.format_exc()
            error_log_record = self.env['tally.error.log'].create({
                'date': fields.Datetime.now(),
                'integration_name': 'UOM Integration',
                'remark': f'Error sending UOM to Tally: {str(e)}',
                'error_log': error_trace,
                'json_log': f'Exception: {str(e)}\n\nTraceback:\n{error_trace}',
            })
            return {
                'name': _('Integration Error Log'),
                'type': 'ir.actions.act_window',
                'res_model': 'tally.error.log',
                'res_id': error_log_record.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def action_push_customer_to_tally(self):
        self.ensure_one()
        company = self.env.company

        # Step 1: Validate Tally configuration using explicit if checks
        if not company.tally_company_name or not company.tally_company_id or not company.tally_url:
            raise ValidationError(_(
                "Please configure Tally Company Name, Company ID and URL before starting the integration."
            ))

        start_date = fields.Datetime.now()

        # Step 2: Find all Customer records where is_tally is False and coa_type is set
        customer_records = self.env['res.partner'].search([('is_tally', '=', False), ('coa_type', '!=', False)])

        if not customer_records:
            end_date = fields.Datetime.now()
            log_record = self.env['tally.log.details'].create({
                'integration_name': 'Customer Integration',
                'remark': 'All Customer records are already integrated in Tally.',
                'count': 0,
                'start_date': start_date,
                'end_date': end_date,
                'json_log': 'No pending Customer records found.',
            })
            return {
                'name': _('Log Details'),
                'type': 'ir.actions.act_window',
                'res_model': 'tally.log.details',
                'res_id': log_record.id,
                'view_mode': 'form',
                'target': 'current',
            }

        # Step 3, 4, 5: Call action_send_to_tally and process result / error
        try:
            res = customer_records.action_send_to_tally()

            # Mark processed Customers as integrated
            customer_records.write({'is_tally': True})

            end_date = fields.Datetime.now()
            attachment = res.get('attachment') if isinstance(res, dict) else False
            xml_content = res.get('xml_content') if isinstance(res, dict) else ''
            response_obj = res.get('response') if isinstance(res, dict) else None
            response_text = response_obj.text if response_obj and hasattr(response_obj, 'text') else str(response_obj or '')

            log_payload = f"Request XML:\n{xml_content}\n\nResponse:\n{response_text}"

            log_record = self.env['tally.log.details'].create({
                'integration_name': 'Customer Integration',
                'remark': f'Created {len(customer_records)} Customers in Tally',
                'count': len(customer_records),
                'start_date': start_date,
                'end_date': end_date,
                'attachment_ids': [(6, 0, [attachment.id])] if attachment else [(6, 0, [])],
                'json_log': log_payload,
            })

            return {
                'name': _('Log Details'),
                'type': 'ir.actions.act_window',
                'res_model': 'tally.log.details',
                'res_id': log_record.id,
                'view_mode': 'form',
                'target': 'current',
            }
        except ValidationError:
            raise
        except Exception as e:
            error_trace = traceback.format_exc()
            error_log_record = self.env['tally.error.log'].create({
                'date': fields.Datetime.now(),
                'integration_name': 'Customer Integration',
                'remark': f'Error sending Customer to Tally: {str(e)}',
                'error_log': error_trace,
                'json_log': f'Exception: {str(e)}\n\nTraceback:\n{error_trace}',
            })
            return {
                'name': _('Integration Error Log'),
                'type': 'ir.actions.act_window',
                'res_model': 'tally.error.log',
                'res_id': error_log_record.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def action_push_invoice_to_tally(self):
        self.ensure_one()
        company = self.env.company

        # Step 1: Validate Tally configuration using explicit if checks
        if not company.tally_company_name or not company.tally_company_id or not company.tally_url:
            raise ValidationError(_(
                "Please configure Tally Company Name, Company ID and URL before starting the integration."
            ))

        start_date = fields.Datetime.now()

        # Step 2: Find all posted Account Move records where is_tally is False
        invoice_records = self.env['account.move'].search([
            ('state', '=', 'posted'),
            ('is_tally', '=', False),
            ('move_type', 'in', ('out_invoice', 'in_invoice'))
        ])

        if not invoice_records:
            end_date = fields.Datetime.now()
            log_record = self.env['tally.log.details'].create({
                'integration_name': 'Invoice Integration',
                'remark': 'All Invoice records are already integrated in Tally.',
                'count': 0,
                'start_date': start_date,
                'end_date': end_date,
                'json_log': 'No pending Invoice records found.',
            })
            return {
                'name': _('Log Details'),
                'type': 'ir.actions.act_window',
                'res_model': 'tally.log.details',
                'res_id': log_record.id,
                'view_mode': 'form',
                'target': 'current',
            }

        # Step 3, 4, 5: Call action_send_to_tally and process result / error
        try:
            res = invoice_records.action_send_to_tally()

            # Mark processed Invoices as integrated
            invoice_records.write({'is_tally': True})

            end_date = fields.Datetime.now()
            attachment = res.get('attachment') if isinstance(res, dict) else False
            xml_content = res.get('xml_content') if isinstance(res, dict) else ''
            response_obj = res.get('response') if isinstance(res, dict) else None
            response_text = response_obj.text if response_obj and hasattr(response_obj, 'text') else str(response_obj or '')

            log_payload = f"Request XML:\n{xml_content}\n\nResponse:\n{response_text}"

            log_record = self.env['tally.log.details'].create({
                'integration_name': 'Invoice Integration',
                'remark': f'Created {len(invoice_records)} Documents in Tally',
                'count': len(invoice_records),
                'start_date': start_date,
                'end_date': end_date,
                'attachment_ids': [(6, 0, [attachment.id])] if attachment else [(6, 0, [])],
                'json_log': log_payload,
            })

            return {
                'name': _('Log Details'),
                'type': 'ir.actions.act_window',
                'res_model': 'tally.log.details',
                'res_id': log_record.id,
                'view_mode': 'form',
                'target': 'current',
            }
        except ValidationError:
            raise
        except Exception as e:
            error_trace = traceback.format_exc()
            error_log_record = self.env['tally.error.log'].create({
                'date': fields.Datetime.now(),
                'integration_name': 'Invoice Integration',
                'remark': f'Error sending Invoice to Tally: {str(e)}',
                'error_log': error_trace,
                'json_log': f'Exception: {str(e)}\n\nTraceback:\n{error_trace}',
            })
            return {
                'name': _('Integration Error Log'),
                'type': 'ir.actions.act_window',
                'res_model': 'tally.error.log',
                'res_id': error_log_record.id,
                'view_mode': 'form',
                'target': 'current',
            }
