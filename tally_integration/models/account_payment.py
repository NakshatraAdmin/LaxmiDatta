from xml.etree import ElementTree as ET

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    _TALLY_ACTION = 'Create'
    _TALLY_PERSISTED_VIEW = 'Accounting Voucher View'
    _TALLY_CMP_GST_REGISTRATION_TYPE = 'Regular'
    _TALLY_ELIGIBLE_FOR_ITC = 'Yes'
    _TALLY_HAS_CASHFLOW = 'Yes'

    # Existing inbound format
    _TALLY_INBOUND_VOUCHER_TYPE = 'Receipt'
    _TALLY_INBOUND_GST_REGISTRATION_TYPE = 'Unregistered/Consumer'
    _TALLY_INBOUND_NARRATION = 'Auto Generated Voucher'
    _TALLY_INBOUND_ENTERED_BY = 'gellp'
    _TALLY_INBOUND_COUNTRY = 'India'
    _TALLY_INBOUND_VOUCHER_NAME = 'Receipt'
    _TALLY_INBOUND_GST_REGISTRATION_SUFFIX = 'Registration'
    _TALLY_INBOUND_TAX_ADJUSTMENT = 'Default'
    _TALLY_INBOUND_DIFF_ACTUAL_QTY = 'Yes'
    _TALLY_INBOUND_SECURITY_WHEN_ENTERED = 'Yes'
    _TALLY_INBOUND_IS_OPTIONAL = 'No'
    _TALLY_INBOUND_VAT_DUTY_PAID = 'Yes'
    _TALLY_INBOUND_BANK_TRANSACTION_TYPE = 'Cheque/DD'
    _TALLY_INBOUND_BANK_PAYMENT_MODE = 'Transacted'
    _TALLY_INBOUND_BANK_MANUAL_STATUS = 'Reconciled'
    _TALLY_INBOUND_STATUS = 'No'

    # New outbound format provided by user
    _TALLY_OUTBOUND_VOUCHER_TYPE = 'Payment'
    _TALLY_OUTBOUND_VOUCHER_NAME = 'Payment'
    _TALLY_OUTBOUND_VOUCHER_NUMBER_SERIES = 'Default'
    _TALLY_OUTBOUND_BILL_REF_NAME = '110'
    _TALLY_OUTBOUND_BILL_TYPE = 'NEW Ref'
    _TALLY_OUTBOUND_BANK_NAME = 'Bank of India (India)'
    _TALLY_OUTBOUND_INSTRUMENT_NUMBER = '121313'
    _TALLY_OUTBOUND_BANK_TRANSACTION_TYPE = 'Cheque/DD'
    _TALLY_OUTBOUND_BANK_PAYMENT_MODE = 'Transacted'

    def action_send_to_tally(self):
        if not self:
            raise UserError(_("Please select at least one payment."))

        invalid_payments = self.filtered(
            lambda payment: payment.partner_type not in ('customer', 'supplier')
        )
        if invalid_payments:
            raise UserError(_("This action is only available for Customer or Vendor payments."))

        missing_data_payments = self.filtered(
            lambda payment: not payment.partner_id or not payment.journal_id
        )
        if missing_data_payments:
            raise UserError(_("Partner and Journal are required on all selected payments."))

        # companies = self.mapped('company_id')
        # if len(companies) != 1:
        #     raise UserError(_("Please select payments from a single company."))

        company = self.env.company # companies[0]
        self._validate_tally_company(company)
        xml_content = self._generate_tally_xml(company)
        self.call_xml_api(xml_content)
        attachment = self._create_tally_xml_attachment(xml_content)

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def _generate_tally_xml(self, company):
        envelope = ET.Element('ENVELOPE')

        header = ET.SubElement(envelope, 'HEADER')
        ET.SubElement(header, 'TALLYREQUEST').text = 'Import Data'

        body = ET.SubElement(envelope, 'BODY')
        import_data = ET.SubElement(body, 'IMPORTDATA')

        request_desc = ET.SubElement(import_data, 'REQUESTDESC')
        ET.SubElement(request_desc, 'REPORTNAME').text = 'Vouchers'

        static_variables = ET.SubElement(request_desc, 'STATICVARIABLES')
        ET.SubElement(static_variables, 'SVCURRENTCOMPANY').text = company.tally_company_name

        request_data = ET.SubElement(import_data, 'REQUESTDATA')

        for payment in self.sorted(lambda record: (record.date or fields.Date.today(), record.id)):
            if payment.partner_type == 'supplier':
                self._append_outbound_voucher(request_data, company, payment)
            else:
                self._append_inbound_voucher(request_data, company, payment)

        self._indent_xml(envelope)
        return ET.tostring(envelope, encoding='utf-8', xml_declaration=True)

    def _append_inbound_voucher(self, request_data, company, payment):
        tally_message = ET.SubElement(request_data, 'TALLYMESSAGE', {'xmlns:UDF': 'TallyUDF'})
        voucher = ET.SubElement(
            tally_message,
            'VOUCHER',
            {
                'VCHTYPE': self._TALLY_INBOUND_VOUCHER_TYPE,
                'ACTION': self._TALLY_ACTION,
                'OBJVIEW': self._TALLY_PERSISTED_VIEW,
            },
        )

        payment_date = self._format_tally_date(payment.date)
        state_name = payment.partner_id.state_id.name or ''
        country_name = payment.partner_id.country_id.name or self._TALLY_INBOUND_COUNTRY
        partner_name = payment.partner_id.name or ''
        company_bank_name = self._get_inbound_company_bank_account_name(payment)
        registration_name = self._get_registration_name(state_name)
        partner_gstin = payment.partner_id.vat or ''
        narration = payment.memo or self._TALLY_INBOUND_NARRATION
        amount = payment.amount or 0.0

        ET.SubElement(voucher, 'DATE').text = payment_date
        ET.SubElement(voucher, 'VCHSTATUSDATE').text = payment_date
        ET.SubElement(voucher, 'GUID').text = company.tally_company_id
        ET.SubElement(voucher, 'GSTREGISTRATIONTYPE').text = self._TALLY_INBOUND_GST_REGISTRATION_TYPE
        ET.SubElement(voucher, 'STATENAME').text = state_name
        ET.SubElement(voucher, 'NARRATION').text = narration
        ET.SubElement(voucher, 'ENTEREDBY').text = self._TALLY_INBOUND_ENTERED_BY
        ET.SubElement(voucher, 'OBJECTUPDATEACTION').text = 'Alter'
        ET.SubElement(voucher, 'COUNTRYOFRESIDENCE').text = country_name
        ET.SubElement(voucher, 'PLACEOFSUPPLY').text = state_name
        ET.SubElement(voucher, 'VOUCHERTYPENAME').text = self._TALLY_INBOUND_VOUCHER_NAME
        ET.SubElement(voucher, 'PARTYNAME').text = company_bank_name
        ET.SubElement(
            voucher,
            'GSTREGISTRATION',
            {
                'TAXTYPE': 'GST',
                'TAXREGISTRATION': partner_gstin,
            },
        ).text = registration_name
        ET.SubElement(voucher, 'CMPGSTIN').text = partner_gstin
        ET.SubElement(voucher, 'PARTYLEDGERNAME').text = partner_name
        ET.SubElement(voucher, 'VOUCHERNUMBER').text = payment.name or ''
        ET.SubElement(voucher, 'CMPGSTREGISTRATIONTYPE').text = self._TALLY_CMP_GST_REGISTRATION_TYPE
        ET.SubElement(voucher, 'PARTYMAILINGNAME').text = company_bank_name
        ET.SubElement(voucher, 'CMPGSTSTATE').text = state_name
        ET.SubElement(voucher, 'PERSISTEDVIEW').text = self._TALLY_PERSISTED_VIEW
        ET.SubElement(voucher, 'VCHSTATUSTAXADJUSTMENT').text = self._TALLY_INBOUND_TAX_ADJUSTMENT
        ET.SubElement(voucher, 'VCHSTATUSVOUCHERTYPE').text = self._TALLY_INBOUND_VOUCHER_TYPE
        ET.SubElement(voucher, 'VCHSTATUSTAXUNIT').text = registration_name
        ET.SubElement(voucher, 'DIFFACTUALQTY').text = self._TALLY_INBOUND_DIFF_ACTUAL_QTY
        ET.SubElement(voucher, 'ISSECURITYONWHENENTERED').text = self._TALLY_INBOUND_SECURITY_WHEN_ENTERED
        ET.SubElement(voucher, 'ISOPTIONAL').text = self._TALLY_INBOUND_IS_OPTIONAL
        ET.SubElement(voucher, 'EFFECTIVEDATE').text = payment_date
        ET.SubElement(voucher, 'ISELIGIBLEFORITC').text = self._TALLY_ELIGIBLE_FOR_ITC
        ET.SubElement(voucher, 'HASCASHFLOW').text = self._TALLY_HAS_CASHFLOW
        ET.SubElement(voucher, 'ISVATDUTYPAID').text = self._TALLY_INBOUND_VAT_DUTY_PAID

        party_ledger_entry = ET.SubElement(voucher, 'ALLLEDGERENTRIES.LIST')
        ET.SubElement(party_ledger_entry, 'LEDGERNAME').text = partner_name
        ET.SubElement(party_ledger_entry, 'ISPARTYLEDGER').text = 'Yes'
        ET.SubElement(party_ledger_entry, 'AMOUNT').text = self._format_amount(amount)

        bank_ledger_entry = ET.SubElement(voucher, 'ALLLEDGERENTRIES.LIST')
        ET.SubElement(bank_ledger_entry, 'LEDGERNAME').text = company_bank_name
        ET.SubElement(bank_ledger_entry, 'ISDEEMEDPOSITIVE').text = 'Yes'
        ET.SubElement(bank_ledger_entry, 'ISPARTYLEDGER').text = 'Yes'
        ET.SubElement(bank_ledger_entry, 'ISLASTDEEMEDPOSITIVE').text = 'Yes'
        ET.SubElement(bank_ledger_entry, 'AMOUNT').text = self._format_amount(-amount)

        bank_allocation = ET.SubElement(bank_ledger_entry, 'BANKALLOCATIONS.LIST')
        ET.SubElement(bank_allocation, 'DATE').text = payment_date
        ET.SubElement(bank_allocation, 'INSTRUMENTDATE').text = payment_date
        ET.SubElement(bank_allocation, 'BANKERSDATE').text = payment_date
        ET.SubElement(bank_allocation, 'NAME').text = ''
        ET.SubElement(bank_allocation, 'TRANSACTIONTYPE').text = self._TALLY_INBOUND_BANK_TRANSACTION_TYPE
        ET.SubElement(bank_allocation, 'PAYMENTFAVOURING').text = partner_name
        ET.SubElement(bank_allocation, 'STATUS').text = self._TALLY_INBOUND_STATUS
        ET.SubElement(bank_allocation, 'PAYMENTMODE').text = self._TALLY_INBOUND_BANK_PAYMENT_MODE
        ET.SubElement(bank_allocation, 'BANKPARTYNAME').text = partner_name
        ET.SubElement(bank_allocation, 'BANKMANUALSTATUS').text = self._TALLY_INBOUND_BANK_MANUAL_STATUS
        ET.SubElement(bank_allocation, 'AMOUNT').text = self._format_amount(-amount)

    def _append_outbound_voucher(self, request_data, company, payment):
        tally_message = ET.SubElement(request_data, 'TALLYMESSAGE', {'xmlns:UDF': 'TallyUDF'})
        voucher = ET.SubElement(
            tally_message,
            'VOUCHER',
            {
                'VCHTYPE': self._TALLY_OUTBOUND_VOUCHER_TYPE,
                'ACTION': self._TALLY_ACTION,
                'OBJVIEW': self._TALLY_PERSISTED_VIEW,
            },
        )

        payment_date = self._format_tally_date(payment.date)
        partner_name = payment.partner_id.name or ''
        state_name = payment.partner_id.state_id.name or ''
        company_bank_name = self._get_outbound_company_bank_account_name(payment)
        amount = payment.amount or 0.0

        ET.SubElement(voucher, 'DATE').text = payment_date
        ET.SubElement(voucher, 'VCHSTATUSDATE').text = payment_date
        ET.SubElement(voucher, 'GUID').text = company.tally_company_id
        ET.SubElement(voucher, 'VOUCHERTYPENAME').text = self._TALLY_OUTBOUND_VOUCHER_NAME
        ET.SubElement(voucher, 'PARTYLEDGERNAME').text = partner_name
        ET.SubElement(voucher, 'VOUCHERNUMBER').text = payment.name or ''
        ET.SubElement(voucher, 'CMPGSTREGISTRATIONTYPE').text = self._TALLY_CMP_GST_REGISTRATION_TYPE
        ET.SubElement(voucher, 'CMPGSTSTATE').text = state_name
        ET.SubElement(voucher, 'PERSISTEDVIEW').text = self._TALLY_PERSISTED_VIEW
        ET.SubElement(voucher, 'VCHSTATUSVOUCHERTYPE').text = self._TALLY_OUTBOUND_VOUCHER_NAME
        ET.SubElement(voucher, 'EFFECTIVEDATE').text = payment_date
        ET.SubElement(voucher, 'ISELIGIBLEFORITC').text = self._TALLY_ELIGIBLE_FOR_ITC
        ET.SubElement(voucher, 'HASCASHFLOW').text = self._TALLY_HAS_CASHFLOW
        ET.SubElement(voucher, 'VOUCHERNUMBERSERIES').text = self._TALLY_OUTBOUND_VOUCHER_NUMBER_SERIES

        party_ledger_entry = ET.SubElement(voucher, 'ALLLEDGERENTRIES.LIST')
        ET.SubElement(party_ledger_entry, 'LEDGERNAME').text = partner_name
        ET.SubElement(party_ledger_entry, 'ISDEEMEDPOSITIVE').text = 'No'
        ET.SubElement(party_ledger_entry, 'ISPARTYLEDGER').text = 'Yes'
        ET.SubElement(party_ledger_entry, 'ISLASTDEEMEDPOSITIVE').text = 'No'
        ET.SubElement(party_ledger_entry, 'AMOUNT').text = self._format_amount(amount)

        bill_allocation = ET.SubElement(party_ledger_entry, 'BILLALLOCATIONS.LIST')
        ET.SubElement(bill_allocation, 'NAME').text = self._TALLY_OUTBOUND_BILL_REF_NAME
        ET.SubElement(bill_allocation, 'BILLTYPE').text = self._TALLY_OUTBOUND_BILL_TYPE
        ET.SubElement(bill_allocation, 'AMOUNT').text = self._format_amount(amount)

        bank_ledger_entry = ET.SubElement(voucher, 'ALLLEDGERENTRIES.LIST')
        ET.SubElement(bank_ledger_entry, 'LEDGERNAME').text = company_bank_name
        ET.SubElement(bank_ledger_entry, 'ISDEEMEDPOSITIVE').text = 'Yes'
        ET.SubElement(bank_ledger_entry, 'ISPARTYLEDGER').text = 'Yes'
        ET.SubElement(bank_ledger_entry, 'ISLASTDEEMEDPOSITIVE').text = 'Yes'
        ET.SubElement(bank_ledger_entry, 'AMOUNT').text = self._format_amount(-amount)

        bank_allocation = ET.SubElement(bank_ledger_entry, 'BANKALLOCATIONS.LIST')
        ET.SubElement(bank_allocation, 'DATE').text = payment_date
        ET.SubElement(bank_allocation, 'INSTRUMENTDATE').text = payment_date
        ET.SubElement(bank_allocation, 'TRANSACTIONTYPE').text = self._TALLY_OUTBOUND_BANK_TRANSACTION_TYPE
        ET.SubElement(bank_allocation, 'BANKNAME').text = self._TALLY_OUTBOUND_BANK_NAME
        ET.SubElement(bank_allocation, 'PAYMENTFAVOURING').text = partner_name
        ET.SubElement(bank_allocation, 'INSTRUMENTNUMBER').text = self._TALLY_OUTBOUND_INSTRUMENT_NUMBER
        ET.SubElement(bank_allocation, 'PAYMENTMODE').text = self._TALLY_OUTBOUND_BANK_PAYMENT_MODE
        ET.SubElement(bank_allocation, 'BANKPARTYNAME').text = partner_name
        ET.SubElement(bank_allocation, 'AMOUNT').text = self._format_amount(-amount)

    def _validate_tally_company(self, company):
        if not company.tally_company_name or not company.tally_company_id:
            raise UserError(_(
                "Please configure Tally settings.\n\n"
                "Go to:\n"
                "Settings -> General Settings -> Tally Company Details\n\n"
                "Required fields:\n"
                "- Company Name\n"
                "- Company ID\n"
            ))

    def _get_inbound_company_bank_account_name(self, payment):
        bank_name = payment.journal_id.bank_id.name or payment.journal_id.name or ''
        account_number = payment.journal_id.bank_acc_number or ''
        return '  '.join(value for value in [bank_name, account_number] if value) or payment.journal_id.name or ''

    def _get_outbound_company_bank_account_name(self, payment):
        return payment.journal_id.name or payment.journal_id.bank_id.name or ''

    def _get_registration_name(self, state_name):
        return ''

    def _create_tally_xml_attachment(self, xml_content):
        return self.env['ir.attachment'].sudo().create({
            'name': 'Payment Voucher.xml',
            'type': 'binary',
            'raw': xml_content,
            'mimetype': 'application/xml',
            'res_model': self._name,
            'res_id': self[:1].id,
        })

    def _format_tally_date(self, date_value):
        return fields.Date.to_date(date_value).strftime('%Y%m%d')

    def _format_amount(self, value):
        return f'{value:.2f}'

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
                    if "does not exist!" in err_msg and "Ledger" in err_msg:
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
