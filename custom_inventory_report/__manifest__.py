{
    'name': 'Custom Inventory Report',
    'version': '17.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Laxmidatta inventory PDF layout',
    'depends': ['stock', 'custom_quotation_app'],
    'data': [
        'report/report_paperformat_stock.xml',
        'report/report_deliveryslip.xml',
        # 'report/report_picking_operations.xml',
        'report/report_package_barcode.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
