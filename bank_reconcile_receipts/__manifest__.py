{
    'name': 'Bank Reconciliation Receipts & Payments',
    'version': '18.0.1.0.9',
    'category': 'Accounting/Accounting',
    'summary': 'Create customer receipts and vendor payments from bank reconciliation models',
    'description': """
Bank Reconciliation Receipts & Payments
========================================

This module extends bank reconciliation functionality to allow automatic creation
of customer receipts and vendor payments from reconciliation models.

Features:
---------
* New counterpart types: 'receipts' and 'payments' in reconciliation models
* Automatic creation of customer receipts when using 'receipts' counterpart
* Automatic creation of vendor payments when using 'payments' counterpart
* Integration with existing bank reconciliation workflow
* Proper accounting entries and payment matching

Usage:
------
1. Go to Accounting > Configuration > Bank Reconciliation Models
2. Create or edit a reconciliation model
3. Set Counterpart Type to 'Customer Receipts' or 'Vendor Payments'
4. Configure the account and other parameters
5. Use the model in bank reconciliation to automatically create payments

Technical:
----------
* Extends account.reconcile.model with new counterpart types
* Hooks into bank statement reconciliation process
* Creates account.payment records with proper configuration
* Maintains audit trail and proper accounting flows
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'account_accountant',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_reconcile_model_views.xml',
        'views/account_bank_statement_line_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'application': False,
}