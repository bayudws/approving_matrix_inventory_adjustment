# -*- coding: utf-8 -*-

{
    'name': "Approving Matrix Inventory Adjustment",
    'description': """
        Allow users to adjust the inventory.
    """,
    'author': "HashMicro / Prince",
    'website': "http://www.hashmicro.com",
    'category': 'Inventory',
    'version': '1.1.4',
    'depends': ['stock','inventory_approval_matrix', 'branch', 'full_inv_adjustment'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template.xml',
        'views/inv_adj_approve_matrix_views.xml',
        'views/stock_inventory_views.xml',
        'views/stock_config_settings_views.xml'
    ],
    'auto_install': False,
    'installable': True,
    'application': True,
}
