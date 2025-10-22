{
    'name': 'Financial Toolkit',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Complete financial tools package for enhanced accounting workflows',
    'description': """
Financial Toolkit - Complete Accounting Enhancement Package
===========================================================

This module is a comprehensive package that includes all essential financial tools
for enhanced accounting workflows in Odoo 18.

Included Modules:
-----------------

🏦 **Bank Reconciliation Receipts & Payments**
   • Create customer receipts and vendor payments directly from bank reconciliation
   • New counterpart types for reconciliation models
   • Automatic payment creation with proper accounting entries

💳 **Credit Card Journal Management**
   • Enhanced credit card statement processing
   • Credit card payment workflows
   • Specialized views for credit card transactions

🔒 **Journal Partner Restrictions**
   • Control which partners can use specific journals
   • Enhanced security for sensitive payment methods
   • Partner-based journal access control

💰 **Liquidity Journal Actions**
   • Advanced liquidity management tools
   • Enhanced bank and cash journal operations
   • Streamlined cash flow management

🔄 **Account Internal Transfers**
   • Internal transfer management between accounts
   • Automated internal accounting entries
   • Multi-currency internal transfer support

Installation:
-------------
Installing this module will automatically install all the financial tools above.
Each component can be configured independently after installation.

Benefits:
---------
• **One-Click Installation**: Install all financial tools at once
• **Integrated Workflows**: Tools designed to work together seamlessly  
• **Enhanced Productivity**: Streamlined financial operations
• **Complete Solution**: Everything you need for advanced accounting

Usage:
------
After installation, access the enhanced features through:
- Accounting > Bank Reconciliation (Enhanced with payment creation)
- Accounting > Configuration > Journals (Enhanced with restrictions)
- Accounting > Payments (Enhanced workflows)

Technical:
----------
• Compatible with Odoo 18.0
• Modular architecture - each component is independent
• Comprehensive logging and debugging support
• Follows Odoo best practices and conventions
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'account_accountant',
    ],
    'data': [
        'views/financial_toolkit_views.xml',
    ],
    'auto_install': False,
    'installable': True,
    'application': True,
    # Automatically install all financial modules when this is installed
    'auto_install_modules': [
        'bank_reconcile_receipts',
        'credit_card_journal', 
        'journal_partner_restriction',
        'liquidity_journal_actions',
        'account_internal_transfer',
    ],
    # Define the modules that should be installed
    'external_dependencies': {},
    'post_init_hook': '_post_install_hook',
}