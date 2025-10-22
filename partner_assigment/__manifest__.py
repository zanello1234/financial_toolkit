# -*- coding: utf-8 -*-
{
    'name': 'Account Partner Assignment',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Assign partners to payable/receivable accounts from chart of accounts',
    'description': """
Account Partner Assignment
==========================

This module allows you to:
* Assign one or more partners to payable/receivable accounts from the chart of accounts
* Automatically update partner's account settings when assigned to an account
* Manage partner-account relationships efficiently

Features:
---------
* Add partner selection field to chart of accounts for payable/receivable accounts
* Automatic synchronization of partner's default payable/receivable account
* Mass assignment capabilities
* Validation to prevent incorrect assignments
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': ['account'],
    'external_dependencies': {},
    'data': [
        'security/ir.model.access.csv',
        'data/cleanup_actions.xml',
        'views/account_account_views.xml',
        'views/res_partner_views.xml',
        'views/wizard_views.xml',
    ],
    'demo': [],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': False,
    'application': False,
}