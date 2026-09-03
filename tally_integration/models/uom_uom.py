from xml.etree import ElementTree as ET

from odoo import _, fields, models
from odoo.exceptions import UserError
import requests


class UomUom(models.Model):
    _inherit = 'uom.uom'

    is_tally = fields.Boolean(
        string="Sent To Tally",
        default=False,
        copy=False
    )

    def action_send_to_tally(self):
        if not self:
            raise UserError(_("Please select at least one unit of measure."))

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
        # company_name = company.name or ''
        # company_guid = self._get_company_guid(company)

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

        applicable_from = self._get_financial_year_start()

        envelope = ET.Element('ENVELOPE')

        header = ET.SubElement(envelope, 'HEADER')
        ET.SubElement(header, 'TALLYREQUEST').text = 'Import Data'

        body = ET.SubElement(envelope, 'BODY')
        import_data = ET.SubElement(body, 'IMPORTDATA')

        request_desc = ET.SubElement(import_data, 'REQUESTDESC')
        ET.SubElement(request_desc, 'REPORTNAME').text = 'All Masters'

        static_variables = ET.SubElement(request_desc, 'STATICVARIABLES')
        ET.SubElement(static_variables, 'SVCURRENTCOMPANY').text = company_name #"Nakshatra Foundry Unit A"#company_name

        request_data = ET.SubElement(import_data, 'REQUESTDATA')

        for uom in self:
            uqc_code = uom.l10n_in_code or ''
            uqc_name = '%s-%s' % (uqc_code, uom.name or '') if uqc_code else (uom.name or '')
            tally_message = ET.SubElement(request_data, 'TALLYMESSAGE', {'xmlns:UDF': 'TallyUDF'})
            unit = ET.SubElement(
                tally_message,
                'UNIT',
                {
                    'NAME': uqc_code,
                    'RESERVEDNAME': '',
                },
            )
            ET.SubElement(unit, 'NAME').text = uqc_code
            ET.SubElement(unit, 'GUID').text = company_guid #"e328d431-57a0-4ca7-b35e-b849932cb991"#company_guid
            ET.SubElement(unit, 'ISDELETED').text = 'No'
            ET.SubElement(unit, 'ASORIGINAL').text = 'Yes'
            ET.SubElement(unit, 'ISSIMPLEUNIT').text = 'Yes'

            reporting_uqc_details = ET.SubElement(unit, 'REPORTINGUQCDETAILS.LIST')
            ET.SubElement(reporting_uqc_details, 'APPLICABLEFROM').text = applicable_from
            # ET.SubElement(reporting_uqc_details, 'REPORTINGUQCNAME').text = self._get_reporting_uqc_name(uom)
            ET.SubElement(reporting_uqc_details, 'REPORTINGUQCNAME').text = uqc_name

        self._indent_xml(envelope)
        return ET.tostring(envelope, encoding='utf-8', xml_declaration=True)

    def _create_tally_xml_attachment(self, xml_content):
        filename = 'UOM Master.xml'
        return self.env['ir.attachment'].sudo().create({
            'name': filename,
            'type': 'binary',
            'raw': xml_content,
            'mimetype': 'application/xml',
            'res_model': self._name,
            'res_id': self[:1].id,
        })

    def _get_company_guid(self, company):
        # candidate_fields = ('tally_guid', 'guid', 'x_tally_guid', 'x_guid')
        # for field_name in candidate_fields:
        #     if field_name in company._fields and company[field_name]:
        #         return str(company[field_name])
        return str(company.id)

    def _get_financial_year_start(self):
        today = fields.Date.context_today(self)
        year = today.year if today.month >= 4 else today.year - 1
        return f'{year}0401'

    # def _get_reporting_uqc_name(self, uom):
    #     mapped_names = {
    #         'kg': 'KGS-KILOGRAMS',
    #         'kgs': 'KGS-KILOGRAMS',
    #         'kilogram': 'KGS-KILOGRAMS',
    #         'kilograms': 'KGS-KILOGRAMS',
    #         'unit': 'UN-Units',
    #         'units': 'UN-Units',
    #     }
    #     normalized_name = (uom.name or '').strip().lower()
    #     return mapped_names.get(normalized_name, f'{(uom.name or "").upper()}-{uom.name or ""}')

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
