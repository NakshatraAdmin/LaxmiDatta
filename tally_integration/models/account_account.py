from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    tally_name = fields.Char(string="Tally Name")
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
