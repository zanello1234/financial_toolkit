# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Liquidity Journal Actions",
    'version': '18.0.1.0.0',
    "depends": ["account", "account_accountant", "account_internal_transfer"],
    "author": "zanello",
    "website": "https://onlyone.com.ar",
    "license": "AGPL-3",
    "category": "Accounting",
    "summary": "Quick payment, collection and transfer buttons with currency exchange support",
    "description": """
Liquidity Journal Actions
=========================

This module adds quick action buttons to bank and cash journal kanban views:

* Cobrar/Comprar (Collect/Buy) button - Payment form or currency exchange wizard
* Pagar/Vender (Pay/Sell) button - Payment form or currency exchange wizard  
* Transferir (Transfer) button - Intuitive internal transfer wizard with visual icons
* Ver Movimientos (View Movements) - Shows all payments for the journal

Features:
---------
* Smart button labels based on journal currency:
  - Local currency journals: Cobrar/Pagar buttons
  - Foreign currency journals: Comprar/Vender buttons
* Currency exchange wizard for foreign currency operations:
  - Buy/Sell currency with exchange rate input
  - Integration with account_internal_transfer module
  - Automatic paired payment creation
  - Support for different source/destination accounts
* Intuitive internal transfer wizard:
  - Visual interface with origin/destination icons
  - Smart currency detection and exchange rate calculation
  - Multi-currency transfer support
  - Integration with account_internal_transfer module
* Direct integration with Odoo's native payment forms for local currency
* Only visible on bank and cash journals
* Pre-filled forms with appropriate context
    """,
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/currency_exchange_wizard_views.xml",
        "views/internal_transfer_wizard_views.xml",
        "views/account_journal_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}