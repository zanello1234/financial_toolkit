# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Credit Card Journal Manager",
    'version': '18.0.1.13.0',
    "depends": ["account", "account_internal_transfer", "account_accountant"],
    "author": "zanello",
    "website": "https://onlyone.com.ar",
    "license": "AGPL-3",
    "category": "Accounting",
    "summary": "Credit card journal management with payment and statement actions",
    "description": """
Credit Card Journal Manager
===========================

This module adds functionality for credit card journals:

* Pay Credit Card button in kanban view
* Issue Statement button in kanban view
* Specialized actions for credit card management

Features:
---------
* Quick payment action for credit cards
* Statement generation for credit card transactions
* Enhanced kanban view for credit card journals
    """,
    "data": [
        "security/ir.model.access.csv",
        "views/account_journal_views.xml",
        "views/credit_card_payment_wizard_views.xml",
        "views/credit_card_statement_wizard_views.xml",
        "views/statement_line_views.xml",
        "views/account_bank_statement_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}