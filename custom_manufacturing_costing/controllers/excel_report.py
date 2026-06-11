from odoo import http
from odoo.http import request
import io
import xlsxwriter
import base64
from datetime import datetime, timedelta
from collections import defaultdict


class ExcelReportController(http.Controller):

    @http.route('/mrp_workorder/excel_report', type='http', auth="user")
    def excel_report(self, workorder_ids=None, **kwargs):
        if not workorder_ids:
            return request.not_found()

        # Convert string of IDs to list of integers
        workorder_ids = [int(id) for id in workorder_ids.split(',')]

        # Get work orders with related data
        workorders = request.env['mrp.workorder'].browse(workorder_ids).with_context(
            prefetch_fields=True
        )
        if not workorders.exists():
            return request.not_found()

        # First pass to determine maximum number of workers across all work orders
        max_workers = 0
        for wo in workorders:
            line_items = wo.line_ids.sorted(key=lambda r: r.start_date or datetime.min)
            employee_data = defaultdict(lambda: {'done_qty': 0, 'total_cost': 0})
            for line in line_items:
                if line.employee_id:
                    employee_data[line.employee_id]['done_qty'] += line.done_qty or 0
                    employee_data[line.employee_id]['total_cost'] += line.total_cost or 0
            max_workers = max(max_workers, len(employee_data))

        # Create Excel file
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Format styles
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#D9D9D9',
            'font_size': 12,
            'text_wrap': True,
            'border': 1,
            'font_name': 'Calibri'
        })

        title_format = workbook.add_format({
            'bold': True,
            'font_size': 16,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#953735',
            'color': 'white',
            'border': 1,
            'font_name': 'Calibri'
        })

        workcenter_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#FFC000',
            'border': 1,
            'font_name': 'Calibri'
        })

        data_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_name': 'Calibri',
            'text_wrap': True,
        })

        merged_format = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_name': 'Calibri'
        })

        time_format = workbook.add_format({
            'num_format': 'hh:mm',
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'font_name': 'Calibri'
        })

        date_format = workbook.add_format({
            'num_format': 'dd/mm/yyyy',
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'font_name': 'Calibri'
        })

        empty_format = workbook.add_format({
            'border': 1
        })

        worksheet = workbook.add_worksheet('Work Orders Report')

        # Define base columns (A-H)
        base_columns = [
            ('A', 'ITEMNAME -M/O NUMBER OR WORK ORDER NUMBER', 40),
            ('B', 'SELF/CUSTOMER', 15),
            ('C', 'TOTAL OPERATION', 15),
            ('D', 'OPERATIONS', 25),
            ('E', 'OPERATION RATE', 15),
            ('F', 'Date', 20),
            ('G', 'STATUS', 15),
            ('H', 'TOTAL TIME', 10)
        ]

        min_workers = 2
        max_workers = max(min_workers, max(len(employee_data) for wo in workorders))

        worker_columns = []
        for i in range(max_workers):
            worker_num = i + 1
            worker_columns.extend([
                (f'{chr(73 + i * 3)}', f'WORKER {worker_num}', 15),  # I, L, O, etc.
                (f'{chr(74 + i * 3)}', 'DONE QTY', 10),
                (f'{chr(75 + i * 3)}', 'AMOUNT', 15)
            ])

        # Combine all columns
        all_columns = base_columns + worker_columns
        if max_workers > min_workers:  # If we have more than 2 workers
            all_columns.append(('O', 'REMARK', 20))

        # Set column widths
        for col_letter, _, width in all_columns:
            worksheet.set_column(f'{col_letter}:{col_letter}', width)

        # Set row heights
        worksheet.set_row(0, 25)  # Title row
        worksheet.set_row(1, 20)  # Work center row
        worksheet.set_row(2, 30)  # Header row

        # Title row
        last_col_letter = all_columns[-1][0]
        worksheet.merge_range(f'A1:{last_col_letter}1', 'WORK ORDER MANUFACTURING DATA ENTRY FORM', title_format)

        # Work Center row (show only once if same for all)
        workcenter_name = workorders[0].workcenter_id.name
        worksheet.merge_range(f'A2:{last_col_letter}2', f'WORK CENTER :- {workcenter_name}', workcenter_format)

        # Headers row
        headers = [col[1] for col in all_columns]
        for col, header in enumerate(headers):
            worksheet.write(2, col, header, header_format)

        row = 3  # Start from row 4 (0-based index)

        for wo in workorders:
            # Get all line items for this work order sorted by start_date
            line_items = wo.line_ids.sorted(key=lambda r: r.start_date or datetime.min)

            # Group line items by employee and calculate totals
            employee_data = defaultdict(lambda: {'done_qty': 0, 'total_cost': 0})
            for line in line_items:
                if line.employee_id:
                    employee_data[line.employee_id]['done_qty'] += line.done_qty or 0
                    employee_data[line.employee_id]['total_cost'] += line.total_cost or 0

            # Get unique employees
            employees = list(employee_data.keys())

            # Product name and MO number
            product_name = wo.product_id.display_name
            mo_number = wo.production_id.name

            # Determine customer/source
            origin = wo.production_id.origin or ''
            customer = origin if origin.startswith('SO') else 'SELF'

            # Store initial row for merging
            initial_row = row

            # Match the sample layout: each block starts directly with ST-/ET- rows.
            time_rows = []
            if line_items:
                for i, line in enumerate(line_items):
                    time_row = row + (i * 2)
                    time_rows.append(time_row)  # START TIME row
                    time_rows.append(time_row + 1)  # END TIME row
            else:
                time_rows.append(row)  # START TIME row
                time_rows.append(row + 1)  # END TIME row

            total_rows = len(time_rows)

            # Merge ITEMNAME column (A) for all rows of this work order
            worksheet.merge_range(
                row, 0,
                row + total_rows - 1, 0,
                f"{product_name}\nMO:-{mo_number}\nWO:-{wo.name}",
                merged_format
            )

            # Write data in the first row (product row)
            worksheet.write(row, 1, customer, data_format)
            repitation_value = wo.total_operation if wo.total_operation is not None else 0
            worksheet.write(row, 2, repitation_value, data_format)
            worksheet.write(row, 3, wo.name, data_format)
            worksheet.write(row, 4, wo.process_cost or 0, data_format)

            # Merge other columns (B-E) for all rows
            for merge_col in [1, 2, 3, 4]:
                cell_value = ""
                if merge_col == 1:
                    cell_value = customer
                elif merge_col == 2:
                    cell_value = repitation_value
                elif merge_col == 3:
                    cell_value = wo.name
                elif merge_col == 4:
                    cell_value = wo.process_cost or 0

                worksheet.merge_range(
                    row, merge_col,
                    row + total_rows - 1, merge_col,
                    cell_value,
                    merged_format
                )

            # Write worker data on the first row (product row)
            # worker_col = 8  # Starting at column I (0-based index 8)
            # for emp in employees:
            #     data = employee_data[emp]
            #     worksheet.write(row, worker_col, emp.name or "", data_format)
            #     worksheet.write(row, worker_col + 1, data['done_qty'] if data['done_qty'] != 0 else 0, data_format)
            #     worksheet.write(row, worker_col + 2, data['total_cost'] if data['total_cost'] != 0 else 0, data_format)
            #     worker_col += 3
            #
            # # Fill remaining worker columns with empty bordered cells
            # while worker_col < len(all_columns):
            #     worksheet.write(row, worker_col, "", empty_format)
            #     worker_col += 1

            worker_col = 8  # Starting at column I (0-based index 8)
            for i in range(max_workers):
                if i < len(employees):
                    emp = employees[i]
                    data = employee_data[emp]
                    worksheet.write(row, worker_col, emp.name or "", data_format)
                    worksheet.write(row, worker_col + 1, data['done_qty'] if data['done_qty'] != 0 else 0, data_format)
                    worksheet.write(row, worker_col + 2, data['total_cost'] if data['total_cost'] != 0 else 0,
                                    data_format)
                else:
                    # Empty columns for workers that don't exist
                    worksheet.write(row, worker_col, "", empty_format)
                    worksheet.write(row, worker_col + 1, "", empty_format)
                    worksheet.write(row, worker_col + 2, "", empty_format)
                worker_col += 3

            # Fill remaining columns with empty bordered cells
            while worker_col < len(all_columns):
                worksheet.write(row, worker_col, "", empty_format)
                worker_col += 1

            # Write time entries and corresponding WORK STRATEGY dates
            if line_items:
                for i, line in enumerate(line_items):
                    time_row = row + (i * 2)

                    # Match the sample sheet: one Date cell spans each ST/ET pair.
                    if line.date:
                        worksheet.merge_range(time_row, 5, time_row + 1, 5, line.date, date_format)
                    else:
                        worksheet.merge_range(time_row, 5, time_row + 1, 5, "", empty_format)

                    # Write time entries
                    worksheet.write(time_row, 6, "ST-", data_format)
                    if line.start_date:
                        local_start = line.start_date + timedelta(hours=5, minutes=30)
                        worksheet.write_datetime(time_row, 7, local_start, time_format)
                    else:
                        worksheet.write(time_row, 7, "", empty_format)

                    time_row += 1
                    worksheet.write(time_row, 6, "ET-", data_format)
                    if line.end_date:
                        local_end = line.end_date + timedelta(hours=5, minutes=30)
                        worksheet.write_datetime(time_row, 7, local_end, time_format)
                    else:
                        worksheet.write(time_row, 7, "", empty_format)
            else:
                time_row = row
                worksheet.merge_range(time_row, 5, time_row + 1, 5, "", empty_format)
                worksheet.write(time_row, 6, "ST-", data_format)
                worksheet.write(time_row, 7, "", empty_format)

                time_row += 1
                worksheet.write(time_row, 6, "ET-", data_format)
                worksheet.write(time_row, 7, "", empty_format)

            # Fill empty cells with borders
            for r in range(row, row + total_rows):
                for c in range(len(all_columns)):
                    try:
                        if worksheet.table[r][c] is None:
                            worksheet.write(r, c, "", empty_format)
                    except (IndexError, KeyError):
                        worksheet.write(r, c, "", empty_format)

            row += total_rows + 1  # Add empty row between work orders

            # Add borders to empty row
            for c in range(len(all_columns)):
                worksheet.write(row, c, "", empty_format)

            row += 1

        workbook.close()
        output.seek(0)

        return request.make_response(
            output.getvalue(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', 'attachment; filename=Work Order Report.xlsx')
            ]
        )
