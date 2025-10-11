# -*- coding: utf-8 -*-


from odoo import http
from odoo.http import request
import io
import xlsxwriter

class CustomQuotationExcelReportController(http.Controller):
    @http.route('/custom_quotation/excel_report/<int:quotation_id>', type='http', auth='user', csrf=False)
    def get_custom_quotation_excel_report(self, quotation_id):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet("Profit Report")

        title = "PROFIT GENERATION REPORT"
        headers = [
            "BOM VOUCHERS NUMBER", "BOM DATE", "BOM UPDATE DATE", "ITEM NAME",
            "GST RATE", "MATERIAL COST", "ACTUAL DIRECT COST", "INDIRECT COST",
            "GROSS COST", "TOTAL OVERHEAD COST", "NET COST", "MATERIAL PROFIT %",
            "MATERIAL PROFIT AMOUNT", "OVERHEAD COST PROFIT %", "OVERHEAD COST PROFIT AMOUNT",
            "SALE RATE", "GST", "MRP"
        ]

        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter'
        })

        sheet.merge_range('A1:R1', title, title_format)

        for col_num, header in enumerate(headers):
            sheet.write(2, col_num, header)
            sheet.set_column(col_num, col_num, max(len(header) + 2, 15))

        header_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        for col_num, header in enumerate(headers):
            sheet.write(2, col_num, header, header_format)

        center_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter'
        })

        quotation = request.env['custom.quotation'].sudo().browse(quotation_id)

        if quotation:
            row_data = [
                quotation.name or '',
                quotation.quotation_date or '',
                quotation.update_date or '',
                quotation.cq_item_type_id.name if quotation.cq_item_type_id else '',
                self.get_tax_rate(quotation.gst_item_gst_rate),
                quotation.bom_total_amount,
                quotation.actual_direct_overheads,
                quotation.indirect_cost,
                quotation.gross_total,
                quotation.total_overhead_cost,
                quotation.net_cost,
                quotation.profit_material_trading_percentage,
                quotation.profit_material_trading,
                quotation.profit_overhead_trading_percentage,
                quotation.profit_overhead_trading,
                quotation.trading_sale_rate,
                quotation.gst_total_rate_trading,
                quotation.mrp_trading,
            ]

            for col_num, data in enumerate(row_data):
                sheet.write(3, col_num, data, center_format)

        workbook.close()
        output.seek(0)

        response = request.make_response(
            output.read(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', 'attachment; filename="Profit_Report.xlsx"')
            ]
        )
        return response

    def get_tax_rate(self, tax_ids):
        if tax_ids:
            rates = tax_ids.mapped('amount')
            names = tax_ids.mapped('name')
            return ', '.join(f"{name} ({rate})" for name, rate in zip(names, rates))
        return ''
