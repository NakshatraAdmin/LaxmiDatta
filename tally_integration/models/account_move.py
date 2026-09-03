from xml.etree import ElementTree as ET

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import html2plaintext


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_tally = fields.Boolean(
        string="Sent To Tally",
        default=False,
        copy=False
    )

    def action_send_to_tally(self):
        if not self:
            raise UserError(_("Please select at least one invoice or bill."))

        invalid_moves = self.filtered(lambda move: move.move_type not in ('in_invoice', 'out_invoice'))
        if invalid_moves:
            raise UserError(_("This action supports only Customer Invoices and Vendor Bills."))

        company = self.env.company
        other_company_moves = self.filtered(lambda move: move.company_id != company)
        if other_company_moves:
            raise UserError(_("Please select records only from the current company."))

        xml_content = self._generate_tally_xml(company)
        response = self.call_xml_api(xml_content)
        self.write({'is_tally': True})
        attachment = self._create_tally_xml_attachment(xml_content)
        return {
            'xml_content': xml_content,
            'response': response,
            'attachment': attachment,
        }

    def _generate_tally_xml(self, company):
        company_name = company.tally_company_name
        company_guid = company.tally_company_id

        if not company_name or not company_guid:
            raise UserError(_(
                "Please configure Tally settings.\n\n"
                "Go to:\n"
                "Settings → General Settings → Tally Company Details\n\n"
                "Required fields:\n"
                "- Company Name\n"
                "- Company ID\n"
            ))

        envelope = ET.Element('ENVELOPE')
        header = ET.SubElement(envelope, 'HEADER')
        ET.SubElement(header, 'TALLYREQUEST').text = 'Import Data'

        body = ET.SubElement(envelope, 'BODY')
        import_data = ET.SubElement(body, 'IMPORTDATA')
        request_desc = ET.SubElement(import_data, 'REQUESTDESC')
        ET.SubElement(request_desc, 'REPORTNAME').text = 'Vouchers'

        static_variables = ET.SubElement(request_desc, 'STATICVARIABLES')
        ET.SubElement(static_variables, 'SVCURRENTCOMPANY').text = company_name

        request_data = ET.SubElement(import_data, 'REQUESTDATA')
        for move in self.with_company(company):
            if not move.invoice_date and not move.date:
                raise UserError(_("Voucher date is missing for invoice %s. Please set an Invoice Date.") % (move.display_name or move.name))

            invoice_lines = self._get_invoice_lines(move)
            if not invoice_lines:
                raise UserError(_("Please add at least one product line in %s.") % (move.display_name or move.name))

            non_party_lines = move.line_ids.filtered(lambda l: not self._is_party_line(move, l))
            missing_tally_name = non_party_lines.filtered(lambda l: not l.account_id.tally_name).mapped('account_id')
            if missing_tally_name:
                acc_names = ", ".join(f"'{a.name}'" for a in missing_tally_name)
                raise UserError(_("Tally Name is not set for account(s): %s. Please configure Tally Name before proceeding.") % acc_names)

            if move.move_type == 'out_invoice':
                self._append_sales_voucher(request_data, move, invoice_lines, company)
            else:
                self._append_purchase_voucher(request_data, move, invoice_lines, company)

        self._indent_xml(envelope)
        xml_bytes = ET.tostring(envelope, encoding='utf-8', xml_declaration=True)
        xml_str = xml_bytes.decode('utf-8').replace('\x04', '&#4;')
        return xml_str.encode('utf-8')

    def _is_party_line(self, move, line):
        partner = move.partner_id.commercial_partner_id
        if move.move_type == 'in_invoice':
            return line.account_id.account_type == 'liability_payable' or line.account_id == partner.property_account_payable_id
        elif move.move_type == 'out_invoice':
            return line.account_id.account_type == 'asset_receivable' or line.account_id == partner.property_account_receivable_id
        return False

    def _append_sales_voucher(self, request_data, move, invoice_lines, company):
        company_partner = company.partner_id
        partner = move.partner_id.commercial_partner_id
        voucher_date = self._format_date(move.invoice_date or move.date)
        party_name = partner.name or ''
        party_state = self._get_move_state_name(move, partner)
        partner_country = partner.country_id.name or 'India'
        reference = move.ref or move.name or ''
        payment_term = self._get_payment_term_text(move, default='1 Days')
        company_gst_type = self._get_gst_registration_type(company_partner.l10n_in_gst_treatment)
        party_gst_type = self._get_gst_registration_type(self._get_move_gst_treatment(move))

        tally_message = ET.SubElement(request_data, 'TALLYMESSAGE', {'xmlns:UDF': 'TallyUDF'})
        voucher = ET.SubElement(
            tally_message,
            'VOUCHER',
            {'VCHTYPE': 'Sales', 'ACTION': 'Create', 'OBJVIEW': 'Invoice Voucher View'},
        )

        # old_audit_ids = ET.SubElement(voucher, 'OLDAUDITENTRYIDS.tree', {'TYPE': 'Number'})
        # ET.SubElement(old_audit_ids, 'OLDAUDITENTRYIDS').text = '-1'
        ET.SubElement(voucher, 'DATE').text = voucher_date
        ET.SubElement(voucher, 'REFERENCEDATE').text = voucher_date
        ET.SubElement(voucher, 'VCHSTATUSDATE').text = voucher_date
        ET.SubElement(voucher, 'GUID').text = company.tally_company_id or ''
        ET.SubElement(voucher, 'GSTREGISTRATIONTYPE').text = party_gst_type
        ET.SubElement(voucher, 'STATENAME').text = party_state
        ET.SubElement(voucher, 'NARRATION').text = self._get_sales_narration(move)
        ET.SubElement(voucher, 'COUNTRYOFRESIDENCE').text = partner_country
        ET.SubElement(voucher, 'PLACEOFSUPPLY').text = party_state
        ET.SubElement(voucher, 'PARTYNAME').text = party_name
        ET.SubElement(voucher, 'GSTREGISTRATION', {'TAXTYPE': 'GST', 'TAXREGISTRATION': ''}).text = ''
        ET.SubElement(voucher, 'VOUCHERTYPENAME').text = 'Sales'
        ET.SubElement(voucher, 'PARTYLEDGERNAME').text = party_name
        ET.SubElement(voucher, 'VOUCHERNUMBER').text = move.name or 'draft'
        ET.SubElement(voucher, 'BASICBUYERNAME').text = party_name
        ET.SubElement(voucher, 'CMPGSTREGISTRATIONTYPE').text = company_gst_type
        ET.SubElement(voucher, 'REFERENCE').text = reference
        ET.SubElement(voucher, 'PARTYMAILINGNAME').text = party_name
        ET.SubElement(voucher, 'CONSIGNEEMAILINGNAME').text = party_name
        ET.SubElement(voucher, 'CONSIGNEESTATENAME').text = party_state
        ET.SubElement(voucher, 'CMPGSTSTATE').text = party_state
        ET.SubElement(voucher, 'CONSIGNEECOUNTRYNAME').text = partner_country
        ET.SubElement(voucher, 'BASICBASEPARTYNAME').text = party_name
        ET.SubElement(voucher, 'PERSISTEDVIEW').text = 'Invoice Voucher View'
        ET.SubElement(voucher, 'VCHGSTCLASS').text = '\x04 Not Applicable'
        ET.SubElement(voucher, 'VCHENTRYMODE').text = 'Item Invoice'
        ET.SubElement(voucher, 'ISDELETED').text = 'No'
        ET.SubElement(voucher, 'ISOPTIONAL').text = 'No'
        ET.SubElement(voucher, 'EFFECTIVEDATE').text = voucher_date
        ET.SubElement(voucher, 'ISCANCELLED').text = 'No'
        ET.SubElement(voucher, 'IRNCANCELLED').text = 'No'
        ET.SubElement(voucher, 'ISINVOICE').text = 'Yes'

        # for line in invoice_lines:
        #     self._append_sales_inventory_entry(voucher, line, company)

        party_lines = move.line_ids.filtered(lambda l: self._is_party_line(move, l))
        party_line = party_lines[:1]
        party_amount = -(party_line.debit if party_line and party_line.debit else abs(move.amount_total))

        party_ledger = ET.SubElement(voucher, 'LEDGERENTRIES.LIST')
        ET.SubElement(party_ledger, 'LEDGERNAME').text = party_name
        ET.SubElement(party_ledger, 'GSTCLASS').text = '\x04 Not Applicable'
        ET.SubElement(party_ledger, 'ISDEEMEDPOSITIVE').text = 'Yes'
        ET.SubElement(party_ledger, 'LEDGERFROMITEM').text = 'No'
        ET.SubElement(party_ledger, 'ISPARTYLEDGER').text = 'Yes'
        ET.SubElement(party_ledger, 'AMOUNT').text = self._format_number(party_amount)

        bill_allocations = ET.SubElement(party_ledger, 'BILLALLOCATIONS.LIST')
        ET.SubElement(bill_allocations, 'NAME').text = reference
        bill_credit_period = ET.SubElement(bill_allocations, 'BILLCREDITPERIOD')
        bill_credit_period.set('P', payment_term)
        bill_credit_period.text = payment_term
        ET.SubElement(bill_allocations, 'BILLTYPE').text = 'New Ref'
        ET.SubElement(bill_allocations, 'AMOUNT').text = self._format_number(party_amount)

        for line in move.line_ids.filtered(lambda l: not self._is_party_line(move, l)):
            if not line.account_id or not (line.debit or line.credit or line.balance):
                continue
            ledger_entry = ET.SubElement(voucher, 'LEDGERENTRIES.LIST')
            ET.SubElement(ledger_entry, 'LEDGERNAME').text = line.account_id.tally_name or ''
            ET.SubElement(ledger_entry, 'GSTCLASS').text = '\x04 Not Applicable'
            ET.SubElement(ledger_entry, 'ISDEEMEDPOSITIVE').text = 'No'
            ET.SubElement(ledger_entry, 'LEDGERFROMITEM').text = 'No'
            ET.SubElement(ledger_entry, 'ISPARTYLEDGER').text = 'No'
            amt = abs(line.credit - line.debit) if (line.credit or line.debit) else abs(line.balance)
            ET.SubElement(ledger_entry, 'AMOUNT').text = self._format_number(amt)

        self._append_gst_list(voucher)

    def _append_purchase_voucher(self, request_data, move, invoice_lines, company):
        partner = move.partner_id.commercial_partner_id
        company_partner = company.partner_id
        config = self._get_voucher_config()
        voucher_date = self._format_date(move.invoice_date or move.date)
        party_state = self._get_move_state_name(move, partner)
        company_state = company_partner.state_id.name or ''
        partner_country = partner.country_id.name or 'India'
        company_country = company_partner.country_id.name or 'India'
        payment_term_name = self._get_payment_term_text(move, default='30 Days')
        move_gst_type = self._get_gst_registration_type(self._get_move_gst_treatment(move))
        move_reference = move.ref or move.name or ''

        tally_message = ET.SubElement(request_data, 'TALLYMESSAGE', {'xmlns:UDF': 'TallyUDF'})
        voucher = ET.SubElement(
            tally_message,
            'VOUCHER',
            {
                'VCHTYPE': config['voucher_type'],
                'ACTION': 'Create',
                'OBJVIEW': 'Invoice Voucher View',
            },
        )

        address_list = ET.SubElement(voucher, 'ADDRESS.LIST', {'TYPE': 'String'})
        for address_line in self._get_address_lines(partner):
            ET.SubElement(address_list, 'ADDRESS').text = address_line

        ET.SubElement(voucher, 'DATE').text = voucher_date
        ET.SubElement(voucher, 'REFERENCEDATE').text = voucher_date
        ET.SubElement(voucher, 'VCHSTATUSDATE').text = voucher_date
        ET.SubElement(voucher, 'GUID').text = company.tally_company_id or ''
        ET.SubElement(voucher, 'GSTREGISTRATIONTYPE').text = move_gst_type
        ET.SubElement(voucher, 'STATENAME').text = party_state
        ET.SubElement(voucher, 'NARRATION').text = self._get_narration_text(move)
        ET.SubElement(voucher, 'COUNTRYOFRESIDENCE').text = partner_country
        ET.SubElement(voucher, 'PARTYGSTIN').text = partner.vat or ''
        ET.SubElement(voucher, 'PLACEOFSUPPLY').text = party_state
        ET.SubElement(voucher, 'PARTYNAME').text = partner.name or ''
        ET.SubElement(voucher, 'GSTREGISTRATION', {'TAXTYPE': 'GST', 'TAXREGISTRATION': ''}).text = ''
        ET.SubElement(voucher, 'VOUCHERTYPENAME').text = config['voucher_type']
        ET.SubElement(voucher, 'PARTYLEDGERNAME').text = partner.name or ''
        ET.SubElement(voucher, 'VOUCHERNUMBER').text = move.name or 'draft'
        ET.SubElement(voucher, 'BASICBUYERNAME').text = company.tally_company_name or ''
        ET.SubElement(voucher, 'CMPGSTREGISTRATIONTYPE').text = self._get_gst_registration_type(
            company_partner.l10n_in_gst_treatment
        )
        ET.SubElement(voucher, 'REFERENCE').text = move_reference
        ET.SubElement(voucher, 'PARTYMAILINGNAME').text = partner.name or ''
        ET.SubElement(voucher, 'PARTYPINCODE').text = partner.zip or ''
        ET.SubElement(voucher, 'CONSIGNEEMAILINGNAME').text = company.tally_company_name or ''
        ET.SubElement(voucher, 'CONSIGNEESTATENAME').text = company_state
        ET.SubElement(voucher, 'CMPGSTSTATE').text = company_state
        ET.SubElement(voucher, 'CONSIGNEECOUNTRYNAME').text = company_country
        ET.SubElement(voucher, 'BASICBASEPARTYNAME').text = partner.name or ''
        ET.SubElement(voucher, 'PERSISTEDVIEW').text = 'Invoice Voucher View'
        ET.SubElement(voucher, 'VCHSTATUSVOUCHERTYPE').text = config['voucher_type']
        basic_due_date = ET.SubElement(voucher, 'BASICDUEDATEOFPYMT')
        basic_due_date.set('P', payment_term_name)
        basic_due_date.text = payment_term_name
        ET.SubElement(voucher, 'VCHENTRYMODE').text = 'Item Invoice'
        ET.SubElement(voucher, 'ISDELETED').text = 'No'
        ET.SubElement(voucher, 'ISOPTIONAL').text = 'No'
        ET.SubElement(voucher, 'EFFECTIVEDATE').text = voucher_date
        ET.SubElement(voucher, 'ISCANCELLED').text = 'No'
        ET.SubElement(voucher, 'ISEWAYBILLAPPLICABLE').text = 'No'
        ET.SubElement(voucher, 'ISINVOICE').text = 'Yes'

        # for line in invoice_lines:
        #     taxable = self._is_taxable_line(line)
        #     cgst_rate, sgst_rate, igst_rate = self._get_tax_rates(line.tax_ids, company)
        #     subtotal = abs(line.price_subtotal)
        #     line_amount = subtotal * config['line_amount_sign']
        #     quantity_text = self._format_quantity(line.quantity, line.product_uom_id.name)
        #     rate_text = self._format_rate(line.price_unit, line.product_uom_id.name)
        #     product_name = line.product_id.name or ''

        #     inventory_entry = ET.SubElement(voucher, 'ALLINVENTORYENTRIES.LIST')
        #     ET.SubElement(inventory_entry, 'STOCKITEMNAME').text = product_name
        #     ET.SubElement(inventory_entry, 'GSTOVRDNTAXABILITY').text = 'Taxable' if taxable else ''
        #     ET.SubElement(inventory_entry, 'GSTSOURCETYPE').text = 'Stock Item' if taxable else ''
        #     ET.SubElement(inventory_entry, 'GSTITEMSOURCE').text = product_name if taxable else ''
        #     ET.SubElement(inventory_entry, 'HSNSOURCETYPE').text = 'Stock Item' if taxable else ''
        #     ET.SubElement(inventory_entry, 'HSNITEMSOURCE').text = product_name if taxable else ''
        #     ET.SubElement(inventory_entry, 'GSTOVRDNTYPEOFSUPPLY').text = self._get_gst_type_of_supply(line)
        #     ET.SubElement(inventory_entry, 'GSTRATEINFERAPPLICABILITY').text = 'As per Masters/Company'
        #     ET.SubElement(inventory_entry, 'GSTHSNNAME').text = line.product_id.l10n_in_hsn_code or ''
        #     ET.SubElement(inventory_entry, 'GSTHSNINFERAPPLICABILITY').text = 'As per Masters/Company'
        #     ET.SubElement(inventory_entry, 'ISDEEMEDPOSITIVE').text = config['line_is_deemed_positive']
        #     ET.SubElement(inventory_entry, 'ISLASTDEEMEDPOSITIVE').text = config['line_is_deemed_positive']
        #     ET.SubElement(inventory_entry, 'RATE').text = rate_text
        #     ET.SubElement(inventory_entry, 'AMOUNT').text = self._format_number(line_amount)
        #     ET.SubElement(inventory_entry, 'ACTUALQTY').text = quantity_text
        #     ET.SubElement(inventory_entry, 'BILLEDQTY').text = quantity_text

        #     batch_allocations = ET.SubElement(inventory_entry, 'BATCHALLOCATIONS.LIST')
        #     ET.SubElement(batch_allocations, 'GODOWNNAME').text = 'Main Location'
        #     ET.SubElement(batch_allocations, 'BATCHNAME').text = 'Primary Batch'
        #     ET.SubElement(batch_allocations, 'DESTINATIONGODOWNNAME').text = 'Main Location'
        #     ET.SubElement(batch_allocations, 'ORDERNO').text = '\x04 Not Applicable'
        #     ET.SubElement(batch_allocations, 'TRACKINGNUMBER').text = '\x04 Not Applicable'
        #     ET.SubElement(batch_allocations, 'AMOUNT').text = self._format_number(line_amount)
        #     ET.SubElement(batch_allocations, 'ACTUALQTY').text = quantity_text
        #     ET.SubElement(batch_allocations, 'BILLEDQTY').text = quantity_text

        #     accounting_allocations = ET.SubElement(inventory_entry, 'ACCOUNTINGALLOCATIONS.LIST')
        #     ET.SubElement(accounting_allocations, 'LEDGERNAME').text = config['stock_ledger_name']
        #     ET.SubElement(accounting_allocations, 'GSTCLASS').text = '\x04 Not Applicable'
        #     ET.SubElement(accounting_allocations, 'ISDEEMEDPOSITIVE').text = config['line_is_deemed_positive']
        #     ET.SubElement(accounting_allocations, 'LEDGERFROMITEM').text = 'No'
        #     ET.SubElement(accounting_allocations, 'ISPARTYLEDGER').text = 'No'
        #     ET.SubElement(accounting_allocations, 'AMOUNT').text = self._format_number(line_amount)

        #     self._append_rate_details(inventory_entry, 'CGST', 'Based on Value', cgst_rate)
        #     self._append_rate_details(inventory_entry, 'SGST/UTGST', 'Based on Value', sgst_rate)
        #     self._append_rate_details(inventory_entry, 'IGST', 'Based on Value', igst_rate)
        #     self._append_rate_details(inventory_entry, 'Cess', '\x04 Not Applicable')
        #     self._append_rate_details(inventory_entry, 'State Cess', 'Based on Value')

        party_lines = move.line_ids.filtered(lambda l: self._is_party_line(move, l))
        party_line = party_lines[:1]
        party_amount = party_line.credit if party_line and party_line.credit else abs(move.amount_total)

        party_ledger = ET.SubElement(voucher, 'LEDGERENTRIES.LIST')
        ET.SubElement(party_ledger, 'LEDGERNAME').text = partner.name or ''
        ET.SubElement(party_ledger, 'GSTCLASS').text = '\x04 Not Applicable'
        ET.SubElement(party_ledger, 'ISDEEMEDPOSITIVE').text = 'No'
        ET.SubElement(party_ledger, 'LEDGERFROMITEM').text = 'No'
        ET.SubElement(party_ledger, 'ISPARTYLEDGER').text = 'Yes'
        ET.SubElement(party_ledger, 'AMOUNT').text = self._format_number(party_amount)

        bill_allocations = ET.SubElement(party_ledger, 'BILLALLOCATIONS.LIST')
        ET.SubElement(bill_allocations, 'NAME').text = move_reference
        bill_credit_period = ET.SubElement(bill_allocations, 'BILLCREDITPERIOD')
        bill_credit_period.text = payment_term_name
        ET.SubElement(bill_allocations, 'BILLTYPE').text = 'New Ref'
        ET.SubElement(bill_allocations, 'AMOUNT').text = self._format_number(party_amount)

        for line in move.line_ids.filtered(lambda l: not self._is_party_line(move, l)):
            if not line.account_id or not (line.debit or line.credit or line.balance):
                continue
            ledger_entry = ET.SubElement(voucher, 'LEDGERENTRIES.LIST')
            ET.SubElement(ledger_entry, 'LEDGERNAME').text = line.account_id.tally_name or ''
            ET.SubElement(ledger_entry, 'GSTCLASS').text = '\x04 Not Applicable'
            ET.SubElement(ledger_entry, 'ISDEEMEDPOSITIVE').text = 'Yes'
            ET.SubElement(ledger_entry, 'LEDGERFROMITEM').text = 'No'
            ET.SubElement(ledger_entry, 'ISPARTYLEDGER').text = 'No'
            amt = -abs(line.debit - line.credit) if (line.debit or line.credit) else -abs(line.balance)
            ET.SubElement(ledger_entry, 'AMOUNT').text = self._format_number(amt)

        self._append_gst_list(voucher)

    def _append_gst_list(self, voucher):
        gst_list = ET.SubElement(voucher, 'GST.LIST')
        ET.SubElement(gst_list, 'PURPOSETYPE').text = 'GST'
        stat_list = ET.SubElement(gst_list, 'STAT.LIST')
        ET.SubElement(stat_list, 'PURPOSETYPE').text = 'GST'
        ET.SubElement(stat_list, 'STATKEY').text = ''
        ET.SubElement(stat_list, 'ISFETCHEDONLY').text = 'No'
        ET.SubElement(stat_list, 'ISDELETED').text = 'No'

    def _create_tally_xml_attachment(self, xml_content):
        move_types = set(self.mapped('move_type'))
        if move_types == {'out_invoice'}:
            filename = 'Customer Invoice Voucher.xml'
        elif move_types == {'in_invoice'}:
            filename = 'Vendor Bill Voucher.xml'
        else:
            filename = 'Tally Vouchers.xml'

        return self.env['ir.attachment'].sudo().create({
            'name': filename,
            'type': 'binary',
            'raw': xml_content,
            'mimetype': 'application/xml',
            'res_model': self._name,
            'res_id': self[:1].id,
        })

    def _append_rate_details(self, parent, duty_head, valuation_type, rate=None):
        rate_details = ET.SubElement(parent, 'RATEDETAILS.LIST')
        ET.SubElement(rate_details, 'GSTRATEDUTYHEAD').text = duty_head
        ET.SubElement(rate_details, 'GSTRATEVALUATIONTYPE').text = valuation_type
        if rate is not None:
            ET.SubElement(rate_details, 'GSTRATE').text = self._format_number(rate)

    def _get_voucher_config(self):
        return {
            'voucher_type': 'Purchase',
            'stock_ledger_name': 'Purchase',
            'line_amount_sign': -1.0,
            'party_amount_sign': 1.0,
            'tax_amount_sign': -1.0,
            'line_is_deemed_positive': 'Yes',
            'party_is_deemed_positive': 'No',
            'tax_is_deemed_positive': 'Yes',
        }

    def _get_invoice_lines(self, move):
        return move.invoice_line_ids.filtered(
            lambda line: line.product_id and line.display_type in (False, 'product')
        )

    def _get_address_lines(self, partner):
        first_line = ', '.join(filter(None, [partner.street, partner.street2]))
        second_line = ', '.join(filter(None, [partner.city, partner.state_id.name]))
        third_line = '.'.join(filter(None, [partner.country_id.name, partner.zip]))
        return [line for line in [first_line, second_line, third_line] if line]

    def _format_date(self, value):
        date_value = fields.Date.to_date(value) or fields.Date.context_today(self)
        return date_value.strftime('%Y%m%d')

    def _format_number(self, value):
        return f'{value:.2f}'

    def _format_rate(self, value, uom_name):
        rate = self._format_number(value or 0.0)
        return f'{rate}/{uom_name}' if uom_name else rate

    def _format_quantity(self, quantity, uom_name):
        qty = f'{quantity:g}'
        return f'{qty} {uom_name}'.strip()

    def _get_narration_text(self, move):
        return html2plaintext(move.narration or '').strip()

    def _get_sales_narration(self, move):
        # narration = self._get_narration_text(move)
        # if narration:
        #     return narration
        # return 'Sales Entry %s' % (move.name or move.id)
        return html2plaintext(move.narration or '').strip()

    def _get_payment_term_text(self, move, default='1 Days'):
        return move.invoice_payment_term_id.name or default

    def _get_move_gst_treatment(self, move):
        return getattr(move, 'l10n_in_gst_treatment', False) or move.partner_id.commercial_partner_id.l10n_in_gst_treatment

    def _get_move_state_name(self, move, partner):
        move_state = getattr(move, 'l10n_in_state_id', False)
        return (move_state and move_state.name) or partner.state_id.name or ''

    def _get_gst_registration_type(self, value):
        mapping = {
            'regular': 'Regular',
            'composition': 'Composition',
            'unregistered': 'Unregistered',
            'consumer': 'Consumer',
            'overseas': 'Overseas',
            'special_economic_zone': 'Special Economic Zone',
            'deemed_export': 'Deemed Export',
            'uin_holders': 'UIN Holders',
        }
        return mapping.get(value, 'Regular')

    def _is_taxable_line(self, line):
        return any(tax.amount for tax in line.tax_ids.filtered(lambda tax: tax.amount_type in ('percent', 'group')))

    def _get_gst_type_of_supply(self, line):
        return 'Services' if line.product_id.type == 'service' else 'Goods'

    def _get_tax_rates(self, taxes, company):
        expanded_taxes = self.env['account.tax']
        company_taxes = taxes.filtered(lambda tax: not tax.company_id or tax.company_id == company)

        tax_amount = 0.0
        for tax in company_taxes:
            tax_amount += tax.amount

        sub_gst = tax_amount / 2 if tax_amount else 0.0
        return sub_gst, sub_gst, tax_amount

        for tax in company_taxes:
            if tax.amount_type == 'group':
                expanded_taxes |= tax.children_tax_ids.filtered(lambda child: child.amount_type == 'percent')
            elif tax.amount_type == 'percent':
                expanded_taxes |= tax

        cgst_rate = sum(expanded_taxes.filtered(lambda tax: 'cgst' in (tax.name or '').lower()).mapped('amount'))
        sgst_rate = sum(expanded_taxes.filtered(
            lambda tax: 'sgst' in (tax.name or '').lower() or 'utgst' in (tax.name or '').lower()
        ).mapped('amount'))
        igst_rate = sum(expanded_taxes.filtered(lambda tax: 'igst' in (tax.name or '').lower()).mapped('amount'))

        total_rate = sum(expanded_taxes.mapped('amount'))
        if not cgst_rate and not sgst_rate and not igst_rate and total_rate:
            cgst_rate = total_rate / 2.0
            sgst_rate = total_rate / 2.0
        elif not igst_rate and (cgst_rate or sgst_rate):
            igst_rate = cgst_rate + sgst_rate

        return cgst_rate, sgst_rate, igst_rate

    def _get_move_tax_amounts(self, move):
        tax_amounts = {
            'CGST': 0.0,
            'SGST': 0.0,
            'IGST': 0.0,
        }
        amount = move.amount_tax
        sub_tax_amount = amount / 2
        tax_amounts = {
            'CGST': sub_tax_amount,
            'SGST': sub_tax_amount,
            # 'IGST': sub_tax_amount,
        }
        return tax_amounts
        for line in move.line_ids.filtered('tax_line_id'):
            tax_name = (line.tax_line_id.name or '').lower()
            amount = abs(line.amount_currency or line.balance)
            if 'cgst' in tax_name:
                tax_amounts['CGST'] += amount
            elif 'sgst' in tax_name or 'utgst' in tax_name:
                tax_amounts['SGST'] += amount
            elif 'igst' in tax_name:
                tax_amounts['IGST'] += amount
        return tax_amounts

    def call_xml_api(self, xml_content):
        company = self.env.company
        tally_url = company.tally_url
        if not tally_url:
            raise UserError(_(
                "Please configure Tally settings.\n\n"
                "Go to:\n"
                "Settings → General Settings → Tally Company Details\n\n"
                "Required fields:\n"
                "- URL\n"
            ))

        headers = {
            'Content-Type': 'application/xml',
        }

        response = requests.post(
            tally_url,
            data=xml_content,
            headers=headers,
        )

        print("Status Code:", response.status_code)
        print("Response Body:", response.text)

        if response.text:
            try:
                root = ET.fromstring(response.text)
                line_error = root.findtext('.//LINEERROR')
                exceptions = root.findtext('.//EXCEPTIONS')
                errors = root.findtext('.//ERRORS')
                if line_error or (exceptions and int(exceptions) > 0) or (errors and int(errors) > 0):
                    err_msg = line_error or _("Tally returned exceptions during import.")
                    if "Voucher date is missing" in err_msg:
                        err_msg += _(
                            "\n\n--- DIAGNOSTIC HELP ---\n"
                            "1. Tally Educational Mode: If Tally is running without a valid license, it ONLY allows voucher dates on the 1st, 2nd, or last day of the month.\n"
                            "2. Financial Period: Verify that the voucher date falls within the open Financial Year period in Tally (Press Alt+F2 in Tally to set period)."
                        )
                    elif "does not exist!" in err_msg and "Ledger" in err_msg:
                        err_msg += _(
                            "\n\n--- DIAGNOSTIC HELP ---\n"
                            "1. Create Ledger in Tally: Ensure a Ledger with this exact name exists in your Tally company database.\n"
                            "2. Update Chart of Accounts: Go to Accounting → Configuration → Chart of Accounts in Odoo, locate the account, and update its 'Tally Name' field to match the exact ledger name configured in Tally.\n"
                            "3. Customer/Vendor Sync: If this ledger refers to a Customer or Vendor, push the contact to Tally first using the 'Push Customers to Tally' action on the Tally Dashboard."
                        )
                    raise UserError(_("Tally Response Error:\n%s") % err_msg)
            except UserError:
                raise
            except Exception:
                pass

        return response

    def _indent_xml(self, element, level=0):
        indent = '\n' + level * '    '
        if len(element):
            if not element.text or not element.text.strip():
                element.text = indent + '    '
            for child in element:
                self._indent_xml(child, level + 1)
            if not element[-1].tail or not element[-1].tail.strip():
                element[-1].tail = indent
        elif level and (not element.tail or not element.tail.strip()):
            element.tail = indent
