from xml.etree import ElementTree as ET

from odoo import _, fields, models
from odoo.exceptions import UserError
import requests


class ProductCategory(models.Model):
    _inherit = 'product.category'

    def action_send_to_tally(self):
        if not self:
            raise UserError(_("Please select at least one product category."))

        company = self.env.company
        # company = self.env['ir.config_parameter'].sudo()
        xml_content = self._generate_tally_xml(company)
        self.call_xml_api(xml_content)
        # attachment = self._create_tally_xml_attachment(xml_content)
        #
        # return {
        #     'type': 'ir.actions.act_url',
        #     'url': f'/web/content/{attachment.id}?download=true',
        #     'target': 'self',
        # }

    def _generate_tally_xml(self, company):
        print("===company===============",company)
        print("===compacompany.tally_company_name===========",company.tally_company_name)
        # company_name = company.get_param('tally_company_name')
        # company_guid = company.get_param('tally_company_id')
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
        ET.SubElement(request_desc, 'REPORTNAME').text = 'All Masters'

        static_variables = ET.SubElement(request_desc, 'STATICVARIABLES')
        ET.SubElement(static_variables, 'SVCURRENTCOMPANY').text = company_name

        request_data = ET.SubElement(import_data, 'REQUESTDATA')

        for category in self:
            tally_message = ET.SubElement(request_data, 'TALLYMESSAGE', {'xmlns:UDF': 'TallyUDF'})
            stock_group = ET.SubElement(
                tally_message,
                'STOCKGROUP',
                {
                    'NAME': category.name or '',
                    'RESERVEDNAME': '',
                },
            )
            ET.SubElement(stock_group, 'GUID').text = "e328d431-57a0-4ca7-b35e-b849932cb991"#company_guid
            # ET.SubElement(stock_group, 'NAME').text = category.name or ''
            ET.SubElement(stock_group, 'PARENT').text = ''
            # ET.SubElement(stock_group, 'ISSUBLEDGER').text = 'No'
            ET.SubElement(stock_group, 'ISBATCHWISEON').text = 'Yes'
            ET.SubElement(stock_group, 'ISDELETED').text = 'No'

            language_name_list = ET.SubElement(stock_group, 'LANGUAGENAME.LIST')
            name_list = ET.SubElement(language_name_list, 'NAME.LIST', {'TYPE': 'String'})
            ET.SubElement(name_list, 'NAME').text = category.name or ''
            ET.SubElement(language_name_list, 'LANGUAGEID').text = '1033'

        self._indent_xml(envelope)
        return ET.tostring(envelope, encoding='utf-8', xml_declaration=True)

    def _create_tally_xml_attachment(self, xml_content):
        # filename = 'product_categories_tally_%s.xml' % fields.Datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = 'Stock Group Master.xml'
        return self.env['ir.attachment'].sudo().create({
            'name': filename,
            'type': 'binary',
            'raw': xml_content,
            'mimetype': 'application/xml',
            'res_model': self._name,
            'res_id': self[:1].id,
        })

    # def _get_company_guid(self, company):
    #     # candidate_fields = ('tally_guid', 'guid', 'x_tally_guid', 'x_guid')
    #     # for field_name in candidate_fields:
    #     #     print("=====field_name=============",field_name)
    #     #     if field_name in company._fields and company[field_name]:
    #     #         return company[field_name]
    #
    #     return str(company.id)

    # def call_xml_api(self, xml_content):
    #     headers = {'Content-Type': 'application/xml'}
    #     try:
    #         # Example POST request
    #         response = requests.post('http://nakshtrasrv2.tallyinfra.com:9000/', data=xml_content, headers=headers)
    #         response.raise_for_status()  # Raise an exception for bad status codes
    #         print("Status Code:", response.status_code)
    #         print("Response Body:", response.text)
    #     except requests.exceptions.RequestException as e:
    #         print("An error occurred: {e}")

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
