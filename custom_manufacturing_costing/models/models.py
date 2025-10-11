# -*- coding: utf-8 -*-
# from addons.hw_escpos.controllers.main import printer
from odoo import models, fields, api, exceptions, _
from odoo.exceptions import ValidationError
from collections import defaultdict
import xlsxwriter
import io
import base64
from datetime import timedelta
import logging


class MrpWorkOrder(models.Model):
    _inherit = 'mrp.workorder'

    process_cost = fields.Float(string='Process Cost', compute='_compute_process_cost', readonly=False, store=True)
    total_cost = fields.Float(string='Total Cost', compute='_compute_total_cost', store=True)
    labour_cost = fields.Selection(
        selection=[
            ('sticking_work', 'Sticking Work'),
            ('fixed_price', 'Fixed Price'),
            ('based_on_quantity', 'Based on Quantity'),
            ('based_on_repitation', 'Based on Repitation')
        ],
        string='Labour Cost',
        default='based_on_repitation',
    )

    line_ids = fields.One2many('mrp.workorder.line', 'workorder_id', string="Labour Cost Lines")
    employee_assigned_ids = fields.Many2many('hr.employee', string='Assigned Employees', compute='_compute_employee_assigned_ids', inverse='_inverse_employee_assigned_ids', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id', readonly=True)
    no_of_repitation = fields.Integer(string="Nos. of Repitation")
    total_operation = fields.Float(string="Total Operation", compute="_compute_total_operation", store=True)

    datewise_summary_line_ids = fields.One2many(
        "mrp.workorder.datewise.summary",
        "workorder_id",
        string="Datewise Summary",
        compute="_compute_datewise_summary",
        store=True,
    )
    total_done_qty = fields.Float(
        string="Total Done Qty", compute="_compute_done_and_pending", store=False
    )
    total_pending_qty = fields.Float(
        string="Total Pending Qty", compute="_compute_done_and_pending", store=False
    )

    @api.depends("line_ids.done_qty", "total_operation")
    def _compute_done_and_pending(self):
        for record in self:
            total_done = sum(record.line_ids.mapped("done_qty"))
            record.total_done_qty = total_done
            record.total_pending_qty = record.total_operation - total_done

    def button_finish(self):
        _logger = logging.getLogger(__name__)
        for rec in self:
            _logger.info("Finishing Work Order: %s", rec.name)
        result = super().button_finish()
        for rec in self:
            _logger.info(
                "Ops:%s  Done:%s  Pending:%s  (WO %s)",
                rec.total_operation, rec.total_done_qty, rec.total_pending_qty, rec.name
            )
            if rec.total_operation != rec.total_done_qty:
                raise ValidationError(
                    _(
                        "Cannot finish work order “%(name)s”:\n"
                        "- Total operations expected: %(expected)d\n"
                        "- Operations completed:    %(done)d\n\n"
                        "Please complete the remaining operations before clicking *Finish*."
                    )
                    % {
                        "name": rec.name,
                        "expected": rec.total_operation,
                        "done": rec.total_done_qty,
                    }
                )
        return result

    @api.depends("line_ids.done_qty")
    def _compute_datewise_summary(self):
        for record in self:
            summary_lines = []
            grouped = defaultdict(float)
            total_done_upto_date = defaultdict(float)

            # Grouping by date and summing done qty
            for line in sorted(record.line_ids, key=lambda l: l.date):
                grouped[line.date] += line.done_qty

            running_total = 0
            for date in sorted(grouped):
                done_qty = grouped[date]
                running_total += done_qty
                pending_qty = record.total_operation - running_total

                summary_lines.append(
                    (
                        0,
                        0,
                        {
                            "date": date,
                            "done_qty": done_qty,
                            "pending_qty": pending_qty,
                        },
                    )
                )
            record.datewise_summary_line_ids = False
            record.datewise_summary_line_ids = summary_lines

    @api.depends('line_ids.employee_id')
    def _compute_employee_assigned_ids(self):
        for rec in self:
            rec.employee_assigned_ids = rec.line_ids.mapped('employee_id')
    
    def _inverse_employee_assigned_ids(self):
        for rec in self:
            current_employees = rec.line_ids.mapped('employee_id')
            new_employees = rec.employee_assigned_ids
            to_remove = current_employees - new_employees
            if to_remove:
                rec.line_ids.filtered(lambda l: l.employee_id in to_remove).unlink()
            to_add = new_employees - current_employees
            for emp in to_add:
                rec.line_ids.create({
                    'workorder_id': rec.id,
                    'employee_id': emp.id,
                })
    
    @api.onchange('line_ids')
    def _onchange_line_ids(self):
        self.employee_assigned_ids = self.line_ids.mapped('employee_id')

    @api.depends('qty_production', 'no_of_repitation')
    def _compute_total_operation(self):
        for rec in self:
            rec.total_operation = rec.qty_production * rec.no_of_repitation if rec.qty_production or rec.no_of_repitation else 0.00

    @api.depends("production_id","production_id.bom_id","labour_cost")
    def _compute_process_cost(self):
        for workorder in self:
            workorder.process_cost = 0.0  # Default value
            workorder.no_of_repitation = 0  # Default value

            if workorder.production_id and workorder.production_id.bom_id:
                bom = workorder.production_id.bom_id  # Get BoM from Manufacturing Order

                # Find the operation that matches Work Order name
                matching_operations = bom.operation_ids.filtered(lambda op: op.name == workorder.name)
                if matching_operations:
                    operation = matching_operations[0]  # Take the first matching operation
                    workorder.process_cost = operation.process_cost
                    workorder.no_of_repitation = operation.no_of_repitation


    # def workorder_details(self):
    #     for workorder in self:
    #         workorder.process_cost = 0.0  # Default value
    #         workorder.no_of_repitation = 0  # Default value
    #
    #         if workorder.production_id and workorder.production_id.bom_id:
    #             bom = workorder.production_id.bom_id  # Get BoM from Manufacturing Order
    #
    #             matching_operations = bom.operation_ids.filtered(lambda op: op.name == workorder.name)
    #             if matching_operations:
    #                 operation = matching_operations[0]  # Take the first matching operation
    #                 workorder.process_cost = operation.process_cost
    #                 workorder.no_of_repitation = operation.no_of_repitation

    # @api.depends('process_cost', 'move_raw_ids.product_qty', 'no_of_repitation', 'labour_cost')
    @api.depends('process_cost', 'total_operation')
    def _compute_total_cost(self):
        for workorder in self:
            if workorder.process_cost < 0:
                raise exceptions.ValidationError("Process cost cannot be negative.")

            # if workorder.labour_cost == 'based_on_repitation' and workorder.no_of_repitation > 0:
            #     workorder.total_cost = workorder.process_cost * workorder.no_of_repitation
            # else:
            #     total_qty = sum(move.product_qty for move in workorder.move_raw_ids)
            #     workorder.total_cost = total_qty * workorder.process_cost

            if workorder.total_operation and workorder.process_cost:
                workorder.total_cost = workorder.total_operation * workorder.process_cost

    @api.onchange('labour_cost')
    def _onchange_labour_cost(self):
        if self.labour_cost == 'based_on_repitation' or self.labour_cost == 'fixed_price':
            self._update_individual_cost()

    @api.onchange('employee_assigned_ids')
    def _onchange_employee_assigned_ids(self):
        if not self.employee_assigned_ids:
            self.line_ids = [(5, 0, 0)]
            return
        current_line_employee_ids = self.line_ids.mapped('employee_id.id')
        new_employee_ids = self.employee_assigned_ids.ids
        to_remove_ids = set(current_line_employee_ids) - set(new_employee_ids)
        to_add_ids = set(new_employee_ids) - set(current_line_employee_ids)
        commands = []
        if to_remove_ids:
            commands.extend([
                (2, line.id, 0) 
                for line in self.line_ids 
                if line.employee_id.id in to_remove_ids
            ])
        if to_add_ids:
            commands.extend([
                (0, 0, {'employee_id': emp_id}) 
                for emp_id in to_add_ids
            ])
        if commands:
            self.update({'line_ids': commands})
            self._update_individual_cost()

    def _update_individual_cost(self):
        for workorder in self:
            if not workorder.line_ids:
                continue
            num_employees = len(workorder.line_ids)
            if num_employees > 0:
                individual_cost = workorder.total_cost / num_employees
                workorder.line_ids.write({'individual_cost': individual_cost})
            else:
                workorder.line_ids.write({'individual_cost': 0.0})

    @api.model_create_multi
    def create(self, values_list):
        records = super(MrpWorkOrder, self).create(values_list)
        for record in records:
            record._update_individual_cost()
        return records

    def write(self, vals):
        res = super(MrpWorkOrder, self).write(vals)
        self._update_individual_cost()
        return res

    def action_print_workorder_excel(self):
        return {
            'type': 'ir.actions.act_url',
            'url': f'/mrp_workorder/excel_report?workorder_ids={",".join(str(id) for id in self.ids)}',
            'target': 'new',
        }

class MrpWorkOrderLine(models.Model):
    _name = 'mrp.workorder.line'
    _description = 'Work Order Line'

    workorder_id = fields.Many2one('mrp.workorder', string="Work Order")
    employee_id = fields.Many2one('hr.employee', string="Employee")
    individual_cost = fields.Float(string="Individual Cost")
    date = fields.Date(string="Date", default=fields.Date.today)
    done_qty = fields.Float(string="Done Qty.")
    total_cost = fields.Float(string="Total Cost", compute="_compute_done_qty", store=True)
    start_date = fields.Datetime(string="Start Datetime")
    end_date = fields.Datetime(string="End Datetime")
    duration = fields.Float(string="Duration (Hours)", compute="_compute_duration", store=True)
    qty_production = fields.Float(
        string='Product Quantity',
        compute='_compute_qty_production',
        store=True
    )
    product_id = fields.Many2one(related="workorder_id.product_id", string="Product Name", store=True)
    production_id = fields.Many2one(related="workorder_id.production_id",string="MO No / WO No", store=True)
    workorder_name = fields.Char(related="workorder_id.name",string="Operation", store=True)
    no_of_repitation = fields.Integer(related="workorder_id.no_of_repitation",string="Number of Repetition")
    total_operation = fields.Float(related="workorder_id.total_operation",string="Total Operation Cost")
    operation_rate = fields.Float(related="workorder_id.total_cost", string="Operation Rate")
    process_cost = fields.Float(related="workorder_id.process_cost", string="Process Cost")

    # @api.depends('workorder_id.production_id.mrp_production_backorder_count', 'workorder_id.qty_production')
    def _compute_qty_production(self):
        for line in self:
            production = line.workorder_id.production_id
            if production.mrp_production_backorder_count > 1:
                line.qty_production = production.mrp_production_backorder_count
            else:
                line.qty_production = line.workorder_id.qty_production

    @api.model
    def cron_recompute_qty_production(self):
        lines = self.search([])
        lines._compute_qty_production()

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                delta = rec.end_date - rec.start_date
                rec.duration = delta.total_seconds() / 3600.0  # Convert seconds to hours
            else:
                rec.duration = 0.0

    @api.depends('done_qty', 'workorder_id.process_cost')
    def _compute_done_qty(self):
        for rec in self:
            if rec.done_qty and rec.workorder_id.process_cost:
                rec.total_cost = rec.done_qty * rec.workorder_id.process_cost
            else:
                rec.total_cost = 0.00

    @api.constrains('done_qty', 'workorder_id')
    def _check_done_qty_total(self):
        for line in self:
            if line.workorder_id:
                total_done_qty = sum(line.workorder_id.line_ids.mapped('done_qty'))
                if total_done_qty > line.workorder_id.total_operation:
                    raise ValidationError(_(
                        "Total Done Qty (%s) exceeds the Total Operation (%s) for Work Order '%s'."
                    ) % (total_done_qty, line.workorder_id.total_operation, line.workorder_id.name))

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.workorder_id and record.employee_id:
                record.workorder_id.employee_assigned_ids = [
                    (4, record.employee_id.id)
                ]
        return records

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            total_done_qty = sum(rec.workorder_id.line_ids.mapped('done_qty'))
            if total_done_qty > total_done_qty:
                raise ValidationError(_(
                    "Total Done Qty (%s) exceeds the Total Operation (%s) for Work Order '%s'."
                ) % (total_done_qty, rec.workorder_id.total_operation, rec.workorder_id.name))
        return res


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    total_component_cost = fields.Float(
        string="Total Component Cost",
        compute='_compute_total_component_cost',
        store=True
    )

    # labour_cost_lines = fields.One2many(
    #     'mrp.workorder.line', 'workorder_id',
    #     string='Labour Cost Lines',
    #     compute='_compute_workorder_lines', store=True
    # )

    related_labour_cost = fields.Selection(
        related='workorder_ids.labour_cost',
        string='Labour Cost',
        readonly=True
    )

    total_component_cost_one_unit = fields.Monetary(
        string='Total Cost Per Unit',
        compute='_compute_total_component_cost_one_unit',
        store=True
    )

    related_orders = fields.One2many(
        'mrp.production', 'origin',
        string='Related Orders',
        compute='_compute_related_orders'
    )
        
    @api.depends('move_raw_ids', 'related_orders')
    def _compute_total_component_cost_one_unit(self):
        for record in self:
            total_cost = 0.0
            for component in record.move_raw_ids:
                if component.product_id:
                    price = component.product_id.standard_price
                    total_cost += price or 0.0

            for related_order in record.related_orders:
                for related_component in related_order.move_raw_ids:
                    if related_component.product_id:
                        price = related_component.product_id.standard_price
                        total_cost += price or 0.0

            record.total_component_cost_one_unit = total_cost

    @api.depends('move_raw_ids', 'related_orders')
    def _compute_total_component_cost(self):
        for production in self:
            total_cost = 0.0
            product_cost_map = {}
            for move in production.move_raw_ids:
                if move.product_id:
                    total_cost += move.product_qty * move.product_id.standard_price
                    product_cost_map[move.product_id.id] = move.product_id.standard_price
            for related_order in production.related_orders:
                total_cost += self._get_total_cost_for_related_order(related_order, product_cost_map)
            production.total_component_cost = total_cost

    def _get_total_cost_for_related_order(self, related_order, product_cost_map):
        total_cost = 0.0
        for move in related_order.move_raw_ids:
            if move.product_id:
                total_cost += move.product_qty * move.product_id.standard_price
                product_cost_map[move.product_id.id] = move.product_id.standard_price

        child_orders = self.env['mrp.production'].search([('origin', '=', related_order.name)])
        for child_order in child_orders:
            for move in child_order.move_raw_ids:
                if move.product_id:
                    total_cost += move.product_qty * move.product_id.standard_price
                    product_cost_map[move.product_id.id] = move.product_id.standard_price
            total_cost += self._get_total_cost_for_related_order(child_order, product_cost_map)
        return total_cost


    def _get_total_cost_of_product(self, product, product_cost_map):
        if product.id in product_cost_map:
            return 0

        product_cost_map[product.id] = product.standard_price
        total_cost = product.standard_price
        related_moves = self.env['stock.move'].search([('product_id', '=', product.id)])
        for move in related_moves:
            if move.product_id:
                child_cost = self._get_total_cost_of_product(move.product_id, product_cost_map)
                total_cost += child_cost
        return total_cost

    # @api.depends('workorder_ids')
    # def _compute_workorder_lines(self):
    #     for production in self:
    #         workorder_lines = self.env['mrp.workorder.line'].search([('workorder_id', 'in', production.workorder_ids.ids)])
    #         production.labour_cost_lines = [(6, 0, workorder_lines.ids)]

    @api.depends('origin')
    def _compute_related_orders(self):
        for production in self:
            related_orders = self.env['mrp.production'].search([('origin', '=', production.name)])
            production.related_orders = related_orders

    def action_print_overview_report(self):
        return self.env.ref(
            "custom_manufacturing_costing.action_report_overview"
        ).report_action(self)

    def get_total_componenet_cost(self):
        for production in self:
            total_cost = sum(
                move.product_qty * move.product_id.standard_price
                for move in production.move_raw_ids
            )
        return total_cost

    def get_total_cost_lab_and_work(self):
        total_labour_cost = sum(self.workorder_ids.line_ids.mapped("individual_cost"))
        total_workorder_cost = 0.0
        for workorder in self.workorder_ids:
            total_workorder_cost += workorder.workcenter_id.costs_hour
        total_cost = total_labour_cost + total_workorder_cost
        return total_cost

    def get_all_child_mos(self):
        def get_child_mos(mo, component_products, all_childs):
            # Filter child MOs based on component products
            for child_mo in mo._get_children().filtered(
                lambda c: c.product_id.id in component_products
            ):
                all_childs.append(child_mo)
                # Get products for the child MO
                child_component_products = child_mo.move_raw_ids.mapped(
                    "product_id"
                ).ids
                # Recursively fetch further child MOs
                get_child_mos(child_mo, child_component_products, all_childs)

        all_childs = []
        component_products = self.move_raw_ids.mapped("product_id").ids
        get_child_mos(self, component_products, all_childs)
        return all_childs

    def calculate_total_cost_per_child_dict(self):
        # Recursive function to accumulate cost from child MOs
        def get_cost_from_child_mos(mo, exclude_mo):
            # Skip calculation if the current MO is the one to be excluded (i.e., self)
            if mo == exclude_mo:
                return 0.0

            total_cost = (
                mo.get_total_cost_lab_and_work() + mo.get_total_componenet_cost()
            )
            parent_mo = mo._get_sources()

            if parent_mo:
                total_cost += get_cost_from_child_mos(
                    parent_mo, exclude_mo
                )  # Recursive call
            return total_cost

        all_childs = self.get_all_child_mos()
        mo_childs = self._get_children()
        mo_dict = {}
        for child in all_childs:
            if not child._get_children():
                # Calculate total cost for each child and store it in the dictionary
                mo_dict[child] = get_cost_from_child_mos(child, self)

        return mo_dict

    def get_updated_childs_dict(self):
        """New method to update the dictionary based on the current childs and their value"""
        mo_dict = self.calculate_total_cost_per_child_dict()
        current_childs = self._get_children()
        new_dict = {}
        for key, value in mo_dict.items():
            parent = key
            # Traverse up the hierarchy until a parent is found in current_childs
            while parent not in current_childs:
                parent_sources = parent._get_sources()
                # If no further parent is found, stop the traversal
                if not parent_sources:
                    break
                # Assuming _get_sources() returns a single parent, take the first in the list if multiple exist
                parent = parent_sources[
                    0
                ]  # Adjust if _get_sources() returns multiple parents and you need different handling

            # If we found a parent in current_childs, perform the update
            if parent in current_childs:
                new_dict[parent.product_id.id] = value
        return new_dict



class ProductDetails(models.Model):
    _name = 'product.details'
    _description = 'Product Details'

    production_id = fields.Many2one('mrp.production', string='Production')
    name = fields.Char(string='Product Name')
    quantity = fields.Float(string='Quantity')
    uom = fields.Many2one('uom.uom', string='Unit of Measure')
    standard_price = fields.Float(string='Standard Price')
    indent_level = fields.Integer(string='Indent Level', default=0)
