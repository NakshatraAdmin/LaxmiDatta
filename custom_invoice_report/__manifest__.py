{
    'name': 'Custom Invoice Report',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Laxmidatta customer invoice PDF layout',
    # Indian invoices use l10n_in's primary report template.  Inheriting that
    # template lets this layout coexist with its GST/HSN report extensions.
    'depends': ['account', 'sale_management', 'l10n_in', 'custom_quotation_app', 'sales_commission_users'],
    'data': [
        'report/report_invoice.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
