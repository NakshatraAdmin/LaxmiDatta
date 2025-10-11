from odoo import models, fields, api, _

class AssignEmployeeWizard(models.TransientModel):
    _name = 'assign.employee.wizard'
    _description = 'Assign Employees to Work Orders'

    employee_ids = fields.Many2many('hr.employee', string='Employees')
    workorder_ids = fields.Many2many('mrp.workorder', string="Work Orders")

    def action_assign_employees(self):
        for workorder in self.workorder_ids:
            workorder.employee_assigned_ids = [(6, 0, self.employee_ids.ids)]
