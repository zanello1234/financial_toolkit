# © 2025 ADHOC SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
{
    "name": "Credit Card Management Pro",
    "summary": "Complete credit card payment processing and management solution",
    "description": """
Credit Card Management Pro
==========================
Professional solution for comprehensive credit card payment processing, automated accreditation management, and financial reconciliation.

🏆 Key Features:
================
🔹 **Smart Card Plans**: Configure multiple credit card processors with automated fee calculations and accreditation terms
🔹 **Automated Surcharges**: Dynamic surcharge calculation for sales orders based on payment method
🔹 **Batch Transfers**: Streamlined batch processing for credit card settlements with automatic reconciliation
🔹 **Fee Invoice Management**: Generate vendor invoices for processing fees with complete traceability
🔹 **Accreditation Tracking**: Real-time tracking of expected vs actual credit card deposits
🔹 **Tax Deduction Management**: Automated calculation and tracking of withholding taxes
🔹 **Bank Reconciliation**: Seamless integration with bank statement reconciliation
🔹 **Holiday Calendar**: Business day calculations for accurate accreditation date estimation
🔹 **Multi-Currency Support**: Handle multiple currencies and exchange rates
🔹 **Detailed Reporting**: Comprehensive analytics and reporting for credit card operations

💼 Business Benefits:
====================
✅ **Reduce Manual Work**: Automate 90% of credit card accounting processes
✅ **Improve Cash Flow**: Accurate prediction of credit card deposits
✅ **Better Financial Control**: Complete visibility into processing fees and deductions
✅ **Compliance Ready**: Built-in tax deduction management for regulatory compliance
✅ **Scalable Solution**: Handle high-volume credit card transactions efficiently

🎯 Perfect For:
===============
• Retail businesses with high credit card volume
• E-commerce companies processing multiple payment methods
• Restaurants and hospitality businesses
• Professional services firms
• Any business requiring detailed credit card accounting

🔧 Technical Excellence:
========================
• Built on Odoo 18.0 framework
• Clean, maintainable code architecture
• Comprehensive test coverage
• Multi-company support
• API integration ready
• Mobile-friendly interface

Transform your credit card management today with this professional-grade solution!
    """,
    'version': '18.0.1.0.37',
    "category": "Accounting/Payment",
    "website": "www.onlyone.odoo.com",
    "author": "Only One by Martin Zanello",
    "maintainer": "onlyone",
    "license": "LGPL-3",
    "price": 150.00,
    "currency": "USD",
    "installable": True,
    "auto_install": False,
    "application": True,
    "external_dependencies": {
        "python": [],
        "bin": [],
    },
    "depends": [
        "account",
        "sale",
        # "account_payment_pro",  # Temporalmente comentado - verificar disponibilidad
        # "card_installment",     # Temporalmente comentado - verificar disponibilidad
        # "account_bank_statement_import",  # Temporalmente comentado - verificar disponibilidad
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/sequence_data.xml",
        "data/account_journal_data.xml",
        "data/card_plan_data.xml",
        "data/account_data.xml",
        "data/holiday_data.xml",
        "views/card_plan_view.xml",
        "views/holiday_view.xml",
        "views/card_tax_deduction_view.xml",
        "views/sale_order_view.xml",
        "views/account_payment_view.xml",
        "views/account_journal_view.xml",
        "wizards/fee_invoice_wizard_view.xml",
        "views/card_accreditation_view.xml",
        "views/card_reconciliation_view.xml",
        "views/card_batch_transfer_view.xml",
        "views/menu_view.xml",
        "wizards/card_surcharge_wizard_view.xml",
        "wizards/card_transfer_wizard_view.xml",
        "views/card_tax_template_wizard_view.xml",
        "views/card_batch_transfer_wizard_view.xml",
        "views/card_add_accreditations_wizard_view.xml",
        "views/card_add_to_batch_wizard_view.xml",
    ],
    "demo": [
        "demo/card_plan_demo.xml",
        "demo/holiday_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [],
        "web.assets_frontend": [],
    },
}