from xml.etree import ElementTree as ET

from odoo import _, fields, models
from odoo.exceptions import UserError
import requests


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def action_send_to_tally(self):
        if not self:
            raise UserError(_("Please select at least one product."))

        company = self.env.company
        xml_content = self._generate_tally_xml(company)
        self.call_xml_api(xml_content)
        print("========Call==========")
        # attachment = self._create_tally_xml_attachment(xml_content)
        #
        # return {
        #     'type': 'ir.actions.act_url',
        #     'url': f'/web/content/{attachment.id}?download=true',
        #     'target': 'self',
        # }

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
        ET.SubElement(static_variables, 'SVCURRENTCOMPANY').text = company_name

        request_data = ET.SubElement(import_data, 'REQUESTDATA')

        for product in self.with_company(company):
            qty_on_hand = product.qty_available or 0.0
            valuation = qty_on_hand * (product.standard_price or 0.0)
            opening_value = -abs(valuation) if valuation else 0.0
            opening_rate = (valuation / qty_on_hand) if qty_on_hand else 0.0
            cgst_rate, sgst_rate, igst_rate = self._get_gst_rates(product, company)
            uom_name = product.uom_id.name or ''

            if not product.categ_id:
                raise UserError(_("Please set category for product %s") % product.name)

            if not product.l10n_in_hsn_code:
                raise UserError(_("Please set HSN/SAC Code for product %s") % product.name)

            tally_message = ET.SubElement(request_data, 'TALLYMESSAGE', {'xmlns:UDF': 'TallyUDF'})
            stock_item = ET.SubElement(
                tally_message,
                'STOCKITEM',
                {
                    'NAME': product.name or '',
                    'RESERVEDNAME': '',
                },
            )

            # mailing_name_list = ET.SubElement(stock_item, 'MAILINGNAME.LIST', {'TYPE': 'String'})
            # ET.SubElement(mailing_name_list, 'MAILINGNAME').text = product.default_code or product.name or ''
            ET.SubElement(stock_item, 'GUID').text = company_guid
            ET.SubElement(stock_item, 'PARENT').text = product.categ_id.name or ''
            ET.SubElement(stock_item, 'GSTAPPLICABLE').text = '\x04 Applicable'
            ET.SubElement(stock_item, 'GSTTYPEOFSUPPLY').text = self._get_gst_type_of_supply(product)
            ET.SubElement(stock_item, 'BASEUNITS').text = uom_name
            ET.SubElement(stock_item, 'ISDELETED').text = 'No'
            ET.SubElement(stock_item, 'OPENINGBALANCE').text = self._format_number(qty_on_hand)
            ET.SubElement(stock_item, 'OPENINGVALUE').text = self._format_number(opening_value)
            ET.SubElement(stock_item, 'OPENINGRATE').text = self._format_rate(opening_rate, uom_name)

            gst_details = ET.SubElement(stock_item, 'GSTDETAILS.LIST')
            ET.SubElement(gst_details, 'APPLICABLEFROM').text = applicable_from
            ET.SubElement(gst_details, 'TAXABILITY').text = 'Taxable'
            ET.SubElement(gst_details, 'SRCOFGSTDETAILS').text = 'Specify Details Here'
            ET.SubElement(gst_details, 'GSTCALCSLABONMRP').text = 'No'
            ET.SubElement(gst_details, 'ISREVERSECHARGEAPPLICABLE').text = 'No'
            ET.SubElement(gst_details, 'ISNONGSTGOODS').text = 'No'
            ET.SubElement(gst_details, 'GSTINELIGIBLEITC').text = 'No'
            ET.SubElement(gst_details, 'INCLUDEEXPFORSLABCALC').text = 'No'

            statewise_details = ET.SubElement(gst_details, 'STATEWISEDETAILS.LIST')
            ET.SubElement(statewise_details, 'STATENAME').text = '\x04 Any'

            # self._append_rate_details(statewise_details, 'CGST', 'Based on Value', cgst_rate)
            # self._append_rate_details(statewise_details, 'SGST/UTGST', 'Based on Value', sgst_rate)
            # self._append_rate_details(statewise_details, 'IGST', 'Based on Value', igst_rate)
            tax_amount = 0.0
            for tax in product.taxes_id:
                tax_amount += tax.amount
            sub_gst = tax_amount / 2 if tax_amount else 0.0
            self._append_rate_details(statewise_details, 'CGST', 'Based on Value', sub_gst)
            self._append_rate_details(statewise_details, 'SGST/UTGST', 'Based on Value', sub_gst)
            self._append_rate_details(statewise_details, 'IGST', 'Based on Value', tax_amount)

            self._append_rate_details(statewise_details, 'Cess', '\x04 Not Applicable')
            self._append_rate_details(statewise_details, 'State Cess', 'Based on Value')
            ET.SubElement(statewise_details, 'GSTSLABRATES.LIST')

            hsn_details = ET.SubElement(stock_item, 'HSNDETAILS.LIST')
            ET.SubElement(hsn_details, 'APPLICABLEFROM').text = applicable_from
            ET.SubElement(hsn_details, 'HSNCODE').text = product.l10n_in_hsn_code or ''
            ET.SubElement(hsn_details, 'SRCOFHSNDETAILS').text = 'Specify Details Here'

            language_name_list = ET.SubElement(stock_item, 'LANGUAGENAME.LIST')
            name_list = ET.SubElement(language_name_list, 'NAME.LIST', {'TYPE': 'String'})
            ET.SubElement(name_list, 'NAME').text = product.name or ''
            ET.SubElement(language_name_list, 'LANGUAGEID').text = '1033'

            reporting_uom = ET.SubElement(stock_item, 'REPORTINGUOMDETAILS.LIST')
            ET.SubElement(reporting_uom, 'APPLICABLEFROM').text = applicable_from
            ET.SubElement(reporting_uom, 'REPORTINGUOMNAME').text = uom_name

            standard_cost = ET.SubElement(stock_item, 'STANDARDCOSTLIST.LIST')
            ET.SubElement(standard_cost, 'DATE').text = applicable_from
            ET.SubElement(standard_cost, 'RATE').text = self._format_rate(product.standard_price or 0.0, uom_name)

            standard_price = ET.SubElement(stock_item, 'STANDARDPRICELIST.LIST')
            ET.SubElement(standard_price, 'DATE').text = applicable_from
            ET.SubElement(standard_price, 'RATE').text = self._format_rate(product.list_price or 0.0, uom_name)

        self._indent_xml(envelope)
        # return ET.tostring(envelope, encoding='utf-8', xml_declaration=True)
        xml_bytes = ET.tostring(envelope, encoding='utf-8', xml_declaration=True)
        xml_str = xml_bytes.decode('utf-8')

        # Replace control character with XML entity
        xml_str = xml_str.replace('\x04', '&#4;')

        return xml_str.encode('utf-8')

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
        print("====tally_url==========",tally_url)
        # print("====xml_content==========",xml_content)

        response = requests.post(
            tally_url,
            data=xml_content,
            headers=headers
        )

        # Print response details
        print("Status Code:", response.status_code)
        print("Response Body:", response.text)

    def _append_rate_details(self, parent, duty_head, valuation_type, rate=None):
        rate_details = ET.SubElement(parent, 'RATEDETAILS.LIST')
        ET.SubElement(rate_details, 'GSTRATEDUTYHEAD').text = duty_head
        ET.SubElement(rate_details, 'GSTRATEVALUATIONTYPE').text = valuation_type
        if rate is not None:
            ET.SubElement(rate_details, 'GSTRATE').text = self._format_number(rate)

    def _create_tally_xml_attachment(self, xml_content):
        filename = 'Stock Item Master.xml'
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

    def _get_gst_type_of_supply(self, product):
        return 'Services' if product.type == 'service' else 'Goods'

    def _get_gst_rates(self, product, company):
        if 'taxes_id' not in product._fields:
            return 0.0, 0.0, 0.0

        taxes = product.taxes_id.filtered(lambda tax: tax.company_id == company)
        expanded_taxes = taxes.browse()

        for tax in taxes:
            if tax.amount_type == 'group':
                expanded_taxes |= tax.children_tax_ids.filtered(lambda child: child.amount_type == 'percent')
            elif tax.amount_type == 'percent':
                expanded_taxes |= tax

        cgst_rate = sum(expanded_taxes.filtered(lambda tax: 'cgst' in (tax.name or '').lower()).mapped('amount'))
        sgst_rate = sum(expanded_taxes.filtered(lambda tax: 'sgst' in (tax.name or '').lower() or 'utgst' in (tax.name or '').lower()).mapped('amount'))
        igst_rate = sum(expanded_taxes.filtered(lambda tax: 'igst' in (tax.name or '').lower()).mapped('amount'))

        total_rate = sum(expanded_taxes.mapped('amount'))

        if not cgst_rate and not sgst_rate and total_rate:
            cgst_rate = total_rate / 2.0
            sgst_rate = total_rate / 2.0
        if not igst_rate and total_rate:
            igst_rate = total_rate

        return cgst_rate, sgst_rate, igst_rate

    def _format_number(self, value):
        return f'{value:.2f}'

    def _format_rate(self, value, uom_name):
        rate = self._format_number(value)
        return f'{rate}/{uom_name}' if uom_name else rate

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
