from odoo import http
from odoo.http import request
import io
import xlsxwriter
from datetime import datetime, timedelta
from collections import defaultdict


class ExcelReportController(http.Controller):

    @http.route('/mrp_workorder/excel_report', type='http', auth="user")
    def excel_report(self, workorder_ids=None, **kwargs):
        if not workorder_ids:
            return request.not_found()

        workorder_ids = [int(id) for id in workorder_ids.split(',')]
        workorders = request.env['mrp.workorder'].browse(workorder_ids).with_context(prefetch_fields=True)
        if not workorders.exists():
            return request.not_found()

        # ── Determine max workers across all WOs ──────────────────────────────
        max_workers = 2  # minimum 2 worker columns
        for wo in workorders:
            employee_data = defaultdict(lambda: {'done_qty': 0, 'total_cost': 0})
            for line in wo.line_ids:
                if line.employee_id:
                    employee_data[line.employee_id]['done_qty'] += line.done_qty or 0
                    employee_data[line.employee_id]['total_cost'] += line.total_cost or 0
            max_workers = max(max_workers, len(employee_data))

        # ── Create workbook ───────────────────────────────────────────────────
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # ── Formats ───────────────────────────────────────────────────────────
        font = 'Calibri'

        title_fmt = workbook.add_format({
            'bold': True, 'font_size': 16, 'font_name': font,
            'align': 'center', 'valign': 'vcenter',
            'bg_color': '#953735', 'font_color': 'white', 'border': 1,
        })
        wc_fmt = workbook.add_format({
            'bold': True, 'font_size': 14, 'font_name': font,
            'align': 'center', 'valign': 'vcenter',
            'bg_color': '#FFC000', 'border': 1,
        })
        hdr_fmt = workbook.add_format({
            'bold': True, 'font_size': 12, 'font_name': font,
            'align': 'center', 'valign': 'vcenter',
            'bg_color': '#D9D9D9', 'border': 1, 'text_wrap': True,
        })
        # Columns A–D: wrap + center + vcenter
        merge_fmt = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'font_name': font,
            'text_wrap': True,
        })
        # date, time cells – centred, no wrap needed
        data_fmt = workbook.add_format({
            'align': 'center', 'valign': 'vcenter',
            'border': 1, 'font_name': font,
        })
        status_fmt = workbook.add_format({
            'align': 'left',
            'valign': 'vcenter',
            'border': 1,
            'font_name': font,
        })
        time_fmt = workbook.add_format({
            'num_format': 'hh:mm',
            'align': 'center', 'valign': 'vcenter',
            'border': 1, 'font_name': font,
        })
        date_fmt = workbook.add_format({
            'num_format': 'dd/mm/yyyy',
            'align': 'center', 'valign': 'vcenter',
            'border': 1, 'font_name': font,
        })
        empty_fmt = workbook.add_format({'border': 1, 'font_name': font})

        ws = workbook.add_worksheet('Work Orders Report')

        # ── Column layout ─────────────────────────────────────────────────────
        # A=ITEMNAME, B=SELF/CUSTOMER, C=TOTAL OPERATION, D=OPERATION RATE,
        # E=Date, F=STATUS, G=TOTAL TIME,
        # then [WORKER n, DONE QTY, AMOUNT] × max_workers,
        # + REMARK at the end

        base_headers = [
            'ITEMNAME -M/O NUMBER OR WORK ORDER NUMBER',  # 0 A
            'SELF/CUSTOMER',                              # 1 B
            'TOTAL OPERATION',                            # 2 C
            'OPERATION RATE',                             # 3 D
            'Date',                                       # 4 E
            'STATUS',                                     # 5 F
            'TOTAL TIME',                                 # 6 G
        ]
        worker_headers = []
        for i in range(max_workers):
            worker_headers += [f'WORKER {i + 1}', 'DONE QTY', 'AMOUNT']
        all_headers = base_headers + worker_headers

        total_cols = len(all_headers)
        last_col = total_cols - 1  # 0-based

        # ── Column widths ─────────────────────────────────────────────────────
        ws.set_column(0, 0, 27)  # A

        ws.set_column(1, 1, 7)  # B
        ws.set_column(2, 2, 7)  # C
        ws.set_column(3, 3, 7)  # D

        ws.set_column(4, 4, 10)  # E
        ws.set_column(5, 5, 10)  # F

        # G to M width = 9
        ws.set_column(6, min(12, total_cols - 1), 9)

        # Remaining columns after M
        if total_cols > 13:
            ws.set_column(13, total_cols - 1, 9)

        # ── Row heights ───────────────────────────────────────────────────────
        ws.set_row(0, 25)   # Row 1 – title
        ws.set_row(1, 20)   # Row 2 – work centre
        ws.set_row(2, 50)   # Row 3 – headers
        ws.set_default_row(15)

        # ── Title & header rows ───────────────────────────────────────────────
        ws.merge_range(0, 0, 0, last_col, 'WORK ORDER MANUFACTURING DATA ENTRY FORM', title_fmt)

        workcenter_name = workorders[0].workcenter_id.name
        ws.merge_range(1, 0, 1, last_col, f'WORK CENTER :- {workcenter_name}', wc_fmt)

        for col, hdr in enumerate(all_headers):
            ws.write(2, col, hdr, hdr_fmt)

        # ── Data rows ─────────────────────────────────────────────────────────
        ROWS_PER_WO = 8   # 4 ST/ET pairs → 8 rows

        row = 3  # 0-based; data starts at Excel row 4

        for wo in workorders:
            line_items = wo.line_ids.sorted(key=lambda r: r.start_date or datetime.min)

            # Aggregate employee data
            employee_data = defaultdict(lambda: {'done_qty': 0, 'total_cost': 0})
            for line in line_items:
                if line.employee_id:
                    employee_data[line.employee_id]['done_qty'] += line.done_qty or 0
                    employee_data[line.employee_id]['total_cost'] += line.total_cost or 0
            employees = list(employee_data.keys())

            product_name = wo.product_id.display_name
            mo_number = wo.production_id.name
            origin = wo.production_id.origin or ''
            customer = origin if origin.startswith('SO') else 'SELF'
            repeat_val = wo.total_operation if wo.total_operation is not None else 0
            op_rate = wo.process_cost or 0

            last_row = row + ROWS_PER_WO - 1  # inclusive end of this WO block

            # ── Col A-D: merge full 8 rows, wrap + centre ────────────────────
            wo_label = f"{product_name}\nMO:-{mo_number}\nWO:-{wo.name}"
            ws.merge_range(row, 0, last_row, 0, wo_label, merge_fmt)
            ws.merge_range(row, 1, last_row, 1, customer, merge_fmt)
            ws.merge_range(row, 2, last_row, 2, repeat_val, merge_fmt)
            ws.merge_range(row, 3, last_row, 3, op_rate, merge_fmt)

            # ── Col H onwards (workers): merge first pair (rows 0-1 of block) ─
            # Workers are written once per WO on the first ST row merged with
            # the ET row (same layout as col E/F/G).
            worker_col_start = 7  # col index for WORKER 1

            for i in range(max_workers):
                wc = worker_col_start + i * 3
                if i < len(employees):
                    emp = employees[i]
                    data = employee_data[emp]
                    ws.merge_range(row, wc, row + 1, wc, emp.name or '', merge_fmt)
                    ws.merge_range(row, wc + 1, row + 1, wc + 1,
                                   data['done_qty'] or 0, merge_fmt)
                    ws.merge_range(row, wc + 2, row + 1, wc + 2,
                                   data['total_cost'] or 0, merge_fmt)
                else:
                    ws.merge_range(row, wc, row + 1, wc, '', empty_fmt)
                    ws.merge_range(row, wc + 1, row + 1, wc + 1, '', empty_fmt)
                    ws.merge_range(row, wc + 2, row + 1, wc + 2, '', empty_fmt)

            # Fill remaining worker row pairs (rows 2-7) with empty bordered cells
            for pair in range(1, 4):  # pairs 1,2,3 (first pair already written)
                pr = row + pair * 2
                for i in range(max_workers):
                    wc = worker_col_start + i * 3
                    ws.merge_range(pr, wc, pr + 1, wc, '', empty_fmt)
                    ws.merge_range(pr, wc + 1, pr + 1, wc + 1, '', empty_fmt)
                    ws.merge_range(pr, wc + 2, pr + 1, wc + 2, '', empty_fmt)

            # ── Col E/F/G: 4 ST/ET pairs, each pair merges 2 rows ────────────
            if line_items:
                lines_to_use = list(line_items)[:4]  # max 4 pairs

                for pair_idx in range(4):
                    pr = row + pair_idx * 2

                    if pair_idx < len(lines_to_use):
                        line = lines_to_use[pair_idx]

                        # Date
                        if line.date:
                            ws.merge_range(pr, 4, pr + 1, 4, line.date, date_fmt)
                        else:
                            ws.merge_range(pr, 4, pr + 1, 4, '', empty_fmt)

                        # Status
                        ws.write(pr, 5, 'ST-', status_fmt)
                        ws.write(pr + 1, 5, 'ET-', status_fmt)

                        # Total Time (Merged Like Worker Columns)
                        start_time = ''
                        end_time = ''

                        if line.start_date:
                            local_start = line.start_date + timedelta(hours=5, minutes=30)
                            start_time = local_start.strftime('%H:%M')

                        if line.end_date:
                            local_end = line.end_date + timedelta(hours=5, minutes=30)
                            end_time = local_end.strftime('%H:%M')

                        time_text = f"{start_time}\n{end_time}".strip()

                        ws.merge_range(
                            pr, 6,
                            pr + 1, 6,
                            time_text,
                            merge_fmt
                        )

                    else:
                        # Empty Pair
                        ws.merge_range(pr, 4, pr + 1, 4, '', empty_fmt)

                        ws.write(pr, 5, 'ST-', status_fmt)
                        ws.write(pr + 1, 5, 'ET-', status_fmt)

                        ws.merge_range(pr, 6, pr + 1, 6, '', empty_fmt)

            else:
                for pair_idx in range(4):
                    pr = row + pair_idx * 2

                    ws.merge_range(pr, 4, pr + 1, 4, '', empty_fmt)

                    ws.write(pr, 5, 'ST-', status_fmt)
                    ws.write(pr + 1, 5, 'ET-', status_fmt)

                    ws.merge_range(pr, 6, pr + 1, 6, '', empty_fmt)

        workbook.close()
        output.seek(0)

        return request.make_response(
            output.getvalue(),
            headers=[
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                ('Content-Disposition', 'attachment; filename=Work Order Report.xlsx'),
            ]
        )