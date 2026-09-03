from xml.etree import ElementTree as ET

from odoo import _, fields, models
from odoo.exceptions import UserError
import requests


class ResPartner(models.Model):
    _inherit = 'res.partner'

    coa_type = fields.Selection([
        ('branch_divisions', 'Branch / Divisions'),
        ('capital_account', 'Capital Account'),
        ('reserves_surplus', 'Reserves & Surplus'),
        ('current_assets', 'Current Assets'),
        ('bank_accounts', 'Bank Accounts'),
        ('cash_in_hand', 'Cash-in-Hand'),
        ('deposits_asset', 'Deposits (Asset)'),
        ('loans_advances_asset', 'Loans & Advances (Asset)'),
        ('stock_in_hand', 'Stock-in-Hand'),
        ('sundry_debtors', 'Sundry Debtors'),
        ('current_liabilities', 'Current Liabilities'),
        ('duties_taxes', 'Duties & Taxes'),
        ('provisions', 'Provisions'),
        ('sundry_creditors', 'Sundry Creditors'),
        ('direct_expenses', 'Direct Expenses'),
        ('direct_incomes', 'Direct Incomes'),
        ('fixed_assets', 'Fixed Assets'),
        ('indirect_expenses', 'Indirect Expenses'),
        ('indirect_incomes', 'Indirect Incomes'),
        ('investments', 'Investments'),
        ('loans_liability', 'Loans (Liability)'),
        ('bank_od', 'Bank OD A/c'),
        ('secured_loans', 'Secured Loans'),
        ('unsecured_loans', 'Unsecured Loans'),
        ('misc_expenses_asset', 'Misc. Expenses (Asset)'),
        ('purchase_accounts', 'Purchase Accounts'),
        ('sales_accounts', 'Sales Accounts'),
        ('suspense', 'Suspense A/c'),
    ], string="COA Type")

    is_tally = fields.Boolean(
        string="Sent To Tally",
        default=False,
        copy=False
    )

    def action_send_to_tally(self):
        if not self:
            raise UserError(_("Please select at least one contact."))

        company = self.env.company
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
        company_name = company.tally_company_name or ''
        company_guid = company.tally_company_id or ''

        if not company_name or not company_guid:
            raise UserError(_(
                "Please configure Tally settings.\n\n"
                "Go to:\n"
                "Settings -> General Settings -> Tally Company Details\n\n"
                "Required fields:\n"
                "- Company Name\n"
                "- Company ID\n"
            ))

        applicable_from = self._get_financial_year_start()
        envelope = ET.Element('ENVELOPE')

        header = ET.SubElement(envelope, 'HEADER')
        ET.SubElement(header, 'TALLYREQUEST').text = 'Import Data'

        body = ET.SubElement(envelope, 'BODY')
        import_data = ET.SubElement(body, 'IMPORTDATA')

        request_desc = ET.SubElement(import_data, 'REQUESTDESC')
        ET.SubElement(request_desc, 'REPORTNAME').text = 'All Masters'

        static_variables = ET.SubElement(request_desc, 'STATICVARIABLES')
        ET.SubElement(static_variables, 'SVCURRENTCOMPANY').text = company_name

        request_data = ET.SubElement(import_data, 'REQUESTDATA')

        for partner in self:
            tally_message = ET.SubElement(request_data, 'TALLYMESSAGE', {'xmlns:UDF': 'TallyUDF'})
            ET.SubElement(tally_message, 'GUID').text = company_guid
            partner_guid = self._get_partner_guid(company_guid, partner)

            parent_value = dict(self._fields['coa_type'].selection).get(partner.coa_type)
            print("====parent_value==============",parent_value)
            if not parent_value:
                raise UserError(_("Please set CoA Type for partner %s") % partner.name)

            ledger = ET.SubElement(
                tally_message,
                'LEDGER',
                {
                    'NAME': partner.name or '',
                    'RESERVEDNAME': '',
                },
            )

            ET.SubElement(ledger, 'GUID').text = partner_guid
            # ET.SubElement(ledger, 'CURRENCYNAME').text = self._get_currency_symbol(partner, company)
            ET.SubElement(ledger, 'CURRENCYNAME').text = partner.currency_id.name
            ET.SubElement(ledger, 'PRIORSTATENAME').text = partner.state_id.name or ''
            ET.SubElement(ledger, 'INCOMETAXNUMBER').text = ''
            ET.SubElement(ledger, 'PARENT').text = parent_value #self._get_partner_group(partner)
            ET.SubElement(ledger, 'TAXTYPE').text = 'Others'
            ET.SubElement(ledger, 'BILLCREDITPERIOD').text = self._get_bill_credit_period(partner)
            ET.SubElement(ledger, 'COUNTRYOFRESIDENCE').text = partner.country_id.name or 'India'
            ET.SubElement(ledger, 'LEDGERCOUNTRYISDCODE').text = self._get_mobile_value(partner)
            ET.SubElement(ledger, 'GSTTYPE').text = 'Not Applicable'
            ET.SubElement(ledger, 'ISBILLWISEON').text = 'Yes'
            ET.SubElement(ledger, 'ISCOSTCENTRESON').text = 'No'
            ET.SubElement(ledger, 'ISDELETED').text = 'No'

            language_name_list = ET.SubElement(ledger, 'LANGUAGENAME.LIST')
            name_list = ET.SubElement(language_name_list, 'NAME.LIST', {'TYPE': 'String'})
            ET.SubElement(name_list, 'NAME').text = partner.name or ''
            ET.SubElement(language_name_list, 'LANGUAGEID').text = '1033'

            gst_details = ET.SubElement(ledger, 'LEDGSTREGDETAILS.LIST')
            ET.SubElement(gst_details, 'APPLICABLEFROM').text = applicable_from
            ET.SubElement(gst_details, 'GSTREGISTRATIONTYPE').text = self._get_gst_registration_type(partner)
            ET.SubElement(gst_details, 'PLACEOFSUPPLY').text = partner.state_id.name or ''
            ET.SubElement(gst_details, 'GSTIN').text = partner.vat or ''
            ET.SubElement(gst_details, 'ISOTHTERRITORYASSESSEE').text = 'No'
            ET.SubElement(gst_details, 'CONSIDERPURCHASEFOREXPORT').text = 'No'
            ET.SubElement(gst_details, 'ISTRANSPORTER').text = 'No'
            ET.SubElement(gst_details, 'ISCOMMONPARTY').text = 'No'

            mailing_details = ET.SubElement(ledger, 'LEDMAILINGDETAILS.LIST')
            address_list = ET.SubElement(mailing_details, 'ADDRESS.LIST', {'TYPE': 'String'})
            for address_line in self._get_address_lines(partner):
                ET.SubElement(address_list, 'ADDRESS').text = address_line
            ET.SubElement(mailing_details, 'APPLICABLEFROM').text = applicable_from
            ET.SubElement(mailing_details, 'PINCODE').text = partner.zip or ''
            ET.SubElement(mailing_details, 'MAILINGNAME').text = partner.name or ''
            ET.SubElement(mailing_details, 'STATE').text = partner.state_id.name or ''
            ET.SubElement(mailing_details, 'COUNTRY').text = partner.country_id.name or 'India'

            contact_details = ET.SubElement(ledger, 'CONTACTDETAILS.LIST')
            ET.SubElement(contact_details, 'NAME').text = 'Primary Mobile No.'
            ET.SubElement(contact_details, 'COUNTRYISDCODE').text = self._get_mobile_value(partner)

        self._indent_xml(envelope)
        return ET.tostring(envelope, encoding='utf-8', xml_declaration=True)

    def _create_tally_xml_attachment(self, xml_content):
        return self.env['ir.attachment'].sudo().create({
            'name': 'Partner Ledger Master.xml',
            'type': 'binary',
            'raw': xml_content,
            'mimetype': 'application/xml',
            'res_model': self._name,
            'res_id': self[:1].id,
        })

    def call_xml_api(self, xml_content):
        company = self.env.company
        # tally_url = company.get_param('tally_url')
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
            'Content-Type': 'application/xml'
        }

        response = requests.post(
            tally_url,
            data=xml_content,
            headers=headers
        )

        # Print response details
        print("Status Code:", response.status_code)
        print("Response Body:", response.text)
        return response

    def _get_financial_year_start(self):
        today = fields.Date.context_today(self)
        year = today.year if today.month >= 4 else today.year - 1
        return f'{year}0401'

    def _get_partner_guid(self, company_guid, partner):
        return f'{company_guid}-{partner.id}'

    # def _get_currency_symbol(self, partner, company):
    #     if 'currency_id' in partner._fields and partner.currency_id:
    #         print("=======partner.currency_id.symbol===============",partner.currency_id.symbol)
    #         return partner.currency_id.symbol or ''
    #     if 'property_purchase_currency_id' in partner._fields and partner.property_purchase_currency_id:
    #         print("======partner.property_purchase_currency_id.symbol=======", partner.property_purchase_currency_id.symbol)
    #         return partner.property_purchase_currency_id.symbol or ''
    #     print("=======company.currency_id.symbol===============", company.currency_id.symbol)
    #     return company.currency_id.symbol or ''

    # def _get_partner_group(self, partner):
    #     if partner.supplier_rank >= 1 and partner.customer_rank < 1:
    #         return 'Sundry Creditors'
    #     if partner.customer_rank >= 1:
    #         return 'Sundry Debtors'
    #     if partner.supplier_rank >= 1:
    #         return 'Sundry Creditors'
    #     return 'Sundry Debtors'

    def _get_bill_credit_period(self, partner):
        if 'property_supplier_payment_term_id' in partner._fields and partner.property_supplier_payment_term_id:
            return partner.property_supplier_payment_term_id.name or ''
        if 'property_payment_term_id' in partner._fields and partner.property_payment_term_id:
            return partner.property_payment_term_id.name or ''
        return ''

    def _get_gst_registration_type(self, partner):
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
        return mapping.get(getattr(partner, 'l10n_in_gst_treatment', False), 'Regular')

    def _get_address_lines(self, partner):
        lines = [partner.street or '', partner.street2 or '']
        city_zip = ' '.join(filter(None, [partner.city or '', partner.zip or ''])).strip()
        lines.append(city_zip)
        cleaned_lines = [line for line in lines if line]
        return cleaned_lines or ['']

    def _get_mobile_value(self, partner):
        return partner.phone or ''

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
