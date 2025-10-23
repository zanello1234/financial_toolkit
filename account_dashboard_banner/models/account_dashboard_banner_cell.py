# Copyright 2025 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import timedelta
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.tools import date_utils
from odoo.tools.misc import format_amount, format_date


class AccountDashboardBannerCell(models.Model):
    _name = "account.dashboard.banner.cell"
    _description = "Accounting Dashboard Banner Cell"
    _order = "sequence, id"

    sequence = fields.Integer()
    cell_type = fields.Selection(
        [
            # Ingresos por período
            ("income_fiscalyear", "Fiscal Year-to-date Income"),
            ("income_year", "Year-to-date Income"),
            ("income_quarter", "Quarter-to-date Income"),
            ("income_month", "Month-to-date Income"),
            # KPIs básicos de balances
            ("liquidity", "Liquidity"),
            ("customer_debt", "Customer Debt"),
            ("customer_overdue", "Customer Overdue"),
            ("supplier_debt", "Supplier Debt"),
            ("total_assets", "Total Assets"),
            ("total_liabilities", "Total Liabilities"),
            # Ratios financieros
            ("receivable_payable_ratio", "Receivable/Payable Ratio"),
            # Indicadores de antigüedad
            ("oldest_customer_invoice", "Oldest Overdue Customer Invoice (days)"),
            ("oldest_supplier_invoice", "Oldest Overdue Supplier Invoice (days)"),
            # Contadores
            ("customer_invoices_count", "Customer Invoices Count"),
            ("supplier_bills_count", "Supplier Bills Count"),
            # Contadores de pendientes de conciliar
            ("unreconciled_receivables_count", "Unreconciled Receivables Count"),
            ("unreconciled_payables_count", "Unreconciled Payables Count"),
            ("unreconciled_bank_count", "Unreconciled Bank Statements Count"),
            ("unreconciled_items_count", "Unreconciled Items Count (Custom Accounts)"),
            # KPI genérico para cualquier cuenta
            ("account_balance", "Account Balance"),
            # KPI con operaciones matemáticas entre otros KPIs
            ("kpi_math_operation", "Mathematical Operation Between KPIs"),
            # Créditos y Deudas Fiscales
            ("vat_credit_balance", "VAT Credits Balance"),
            ("vat_debt_balance", "VAT Debts Balance"),
            ("tax_withholdings_balance", "Tax Withholdings Balance"),
            ("social_security_debt", "Social Security Debts"),
            ("income_tax_provision", "Income Tax Provision"),
            ("tax_credits_vs_debts_ratio", "Tax Credits vs Debts Ratio"),
            ("pending_tax_refunds", "Pending Tax Refunds"),
            # Fechas de bloqueo (configuración de empresa)
            ("tax_lock_date", "Tax Return Lock Date"),
            ("sale_lock_date", "Sales Lock Date"),
            ("purchase_lock_date", "Purchase Lock Date"),
            ("fiscalyear_lock_date", "Global Lock Date"),
            ("hard_lock_date", "Hard Lock Date"),
        ],
        required=True,
    )
    custom_label = fields.Char()
    custom_tooltip = fields.Char()
    
    # Toggle para mostrar/ocultar KPI
    active_in_dashboard = fields.Boolean(
        string="Show in Dashboard", 
        default=True, 
        help="Show this KPI in the financial dashboard"
    )
    
    # Categoría para organizar KPIs
    category = fields.Selection([
        ('financial', 'Financial Position'),
        ('liquidity', 'Liquidity & Cash Flow'),
        ('receivables', 'Accounts Receivable'),
        ('payables', 'Accounts Payable'),
        ('performance', 'Performance Metrics'),
        ('aging', 'Aging Analysis'),
        ('profitability', 'Profitability Ratios'),
        ('tax_credits_debts', 'Tax Credits & Fiscal Debts'),
        ('lock_dates', 'Lock Dates'),
        ('other', 'Other KPIs'),
    ], string="Category", default='other', help="Category to organize KPIs in the configuration view")
    
    # Selección específica de cuentas para KPIs personalizados
    specific_account_ids = fields.Many2many(
        'account.account',
        string="Specific Accounts",
        help="Select specific accounts for this KPI (overrides default account selection)"
    )
    
    # Opciones para KPIs de liquidez
    liquidity_mode = fields.Selection([
        ('all_accounts', 'All Liquidity Accounts'),
        ('specific_accounts', 'Specific Accounts Only'),
    ], string="Liquidity Mode", default='all_accounts')
    
    # Opciones para KPIs genéricos por tipo de cuenta
    account_type_filter = fields.Selection([
        ('asset_receivable', 'Receivable'),
        ('asset_cash', 'Bank and Cash'),
        ('asset_current', 'Current Assets'),
        ('asset_non_current', 'Non-current Assets'),
        ('asset_prepayments', 'Prepayments'),
        ('asset_fixed', 'Fixed Assets'),
        ('liability_payable', 'Payable'),
        ('liability_credit_card', 'Credit Card'),
        ('liability_current', 'Current Liabilities'),
        ('liability_non_current', 'Non-current Liabilities'),
        ('equity', 'Equity'),
        ('equity_unaffected', 'Current Year Earnings'),
        ('income', 'Income'),
        ('income_other', 'Other Income'),
        ('expense', 'Expenses'),
        ('expense_depreciation', 'Depreciation'),
        ('expense_direct_cost', 'Direct Costs'),
        ('off_balance', 'Off-Balance Sheet'),
    ], string="Account Type Filter", help="Filter accounts by type for this KPI")
    
    # Modo de selección de cuentas
    account_selection_mode = fields.Selection([
        ('by_type', 'By Account Type'),
        ('specific', 'Specific Accounts'),
        ('legacy', 'Legacy Mode (for existing liquidity KPIs)'),
    ], string="Account Selection Mode", default='by_type', 
       help="How to select accounts for this KPI")
    
    # Acción al hacer click
    click_action = fields.Selection([
        ('none', 'No Action'),
        ('account_move', 'Journal Entries'),
        ('account_account', 'Chart of Accounts'),
        ('res_partner', 'Partners'),
        ('account_payment', 'Payments'),
        ('custom', 'Custom Action'),
    ], string="Click Action", default='none', help="Action to perform when clicking the KPI")
    
    # Dominio para filtrar registros
    action_domain = fields.Text(
        string="Action Domain", 
        help="Domain filter for the action (Python expression)"
    )
    
    warn = fields.Boolean(string="Warning")
    warn_lock_date_days = fields.Integer(
        compute="_compute_warn_fields", store=True, readonly=False, precompute=True
    )
    warn_min = fields.Float(string="Minimum")
    warn_max = fields.Float(string="Maximum")
    warn_type_show = fields.Boolean(
        compute="_compute_warn_fields", store=True, precompute=True
    )
    warn_type = fields.Selection(
        [
            ("under", "Under Minimum"),
            ("above", "Above Maximum"),
            ("outside", "Under Minimum or Above Maximum"),
            ("inside", "Between Minimum and Maximum"),
        ],
        default="under",
    )
    
    # Campos para sistema de colores avanzado (rojo/amarillo/verde)
    use_color_thresholds = fields.Boolean(
        string="Use Color Thresholds",
        default=False,
        help="Enable advanced color system: red (danger), yellow (warning), green (safe)"
    )
    
    # Umbrales de color - para zona amarilla (warning/cerca del límite)
    yellow_threshold_percentage = fields.Float(
        string="Yellow Threshold %",
        default=10.0,
        help="Percentage proximity to min/max limits that triggers yellow color"
    )
    
    # Campos para métricas objetivo y porcentaje alcanzado
    target_value = fields.Float(
        string="Target Value",
        help="Target/goal value for this KPI to calculate achievement percentage"
    )
    
    show_target_percentage = fields.Boolean(
        string="Show Achievement %",
        default=False,
        help="Display percentage of target achieved on the KPI card"
    )

    # Campos para operaciones matemáticas entre KPIs
    math_operation = fields.Selection([
        ('add', 'Addition (+)'),
        ('subtract', 'Subtraction (-)'),
        ('multiply', 'Multiplication (×)'),
        ('divide', 'Division (÷)'),
        ('percentage', 'Percentage (A/B * 100)'),
    ], string="Mathematical Operation", 
       help="Type of mathematical operation to perform between KPIs")
    
    kpi_operand_a_id = fields.Many2one(
        'account.dashboard.banner.cell',
        string="First KPI (A)",
        help="First KPI for the mathematical operation"
    )
    
    kpi_operand_b_id = fields.Many2one(
        'account.dashboard.banner.cell', 
        string="Second KPI (B)",
        help="Second KPI for the mathematical operation"
    )
    
    math_decimal_places = fields.Integer(
        string="Decimal Places",
        default=2,
        help="Number of decimal places to show in the result"
    )
    
    # Formato del resultado para operaciones matemáticas
    math_result_format = fields.Selection([
        ('number', 'Number (1,234.56)'),
        ('currency', 'Currency ($1,234.56)'),
        ('percentage', 'Percentage (12.34%)'),
        ('ratio', 'Ratio (1.23:1)'),
        ('custom', 'Custom Format')
    ], string="Result Format", default='number', 
       help="How to format the mathematical operation result")
    
    math_custom_suffix = fields.Char(
        string="Custom Suffix", 
        help="Custom suffix for the result (e.g., 'days', 'items', 'units')"
    )
    
    # Configuración de valores históricos mín/máx
    show_historical_range = fields.Boolean(
        string="Show Min/Max Range", 
        default=False, 
        help="Show historical minimum and maximum values below the main metric"
    )
    
    historical_period_days = fields.Integer(
        string="Historical Period (Days)", 
        default=0,
        help="Number of days to look back for min/max calculation. Leave 0 to use current data only."
    )
    
    # Campos computados para min/max históricos
    historical_min = fields.Float(
        string="Historical Minimum", 
        default=0.0,
        help="Historical minimum value"
    )
    
    historical_max = fields.Float(
        string="Historical Maximum", 
        default=0.0,
        help="Historical maximum value"
    )

    _sql_constraints = [
        (
            "warn_lock_date_days_positive",
            "CHECK(warn_lock_date_days >= 0)",
            "Warn if lock date is older than N days must be positive or null.",
        )
    ]

    @api.constrains("warn_min", "warn_max", "warn_type", "warn", "cell_type")
    def _check_warn_config(self):
        for cell in self:
            if (
                cell.cell_type
                and not cell.cell_type.endswith("_lock_date")
                and cell.warn
                and cell.warn_type in ("outside", "inside")
                and cell.warn_max <= cell.warn_min
            ):
                cell_type2label = dict(
                    self.fields_get("cell_type", "selection")["cell_type"]["selection"]
                )
                raise ValidationError(
                    _(
                        "On cell '%(cell_type)s' with warning enabled, "
                        "the minimum (%(warn_min)s) must be under "
                        "the maximum (%(warn_max)s).",
                        cell_type=cell_type2label[cell.cell_type],
                        warn_min=cell.warn_min,
                        warn_max=cell.warn_max,
                    )
                )

    @api.constrains("cell_type", "math_operation", "kpi_operand_a_id", "kpi_operand_b_id")
    def _check_math_operation_config(self):
        for cell in self:
            if cell.cell_type == 'kpi_math_operation':
                if not cell.math_operation:
                    raise ValidationError(_("Mathematical operation is required for KPI math operations."))
                if not cell.kpi_operand_a_id:
                    raise ValidationError(_("First KPI (A) is required for mathematical operations."))
                if not cell.kpi_operand_b_id:
                    raise ValidationError(_("Second KPI (B) is required for mathematical operations."))
                if cell.kpi_operand_a_id == cell.kpi_operand_b_id:
                    raise ValidationError(_("First KPI and Second KPI must be different."))
                if cell.kpi_operand_a_id == cell or cell.kpi_operand_b_id == cell:
                    raise ValidationError(_("KPI cannot reference itself in mathematical operations."))
                
                # Check for circular references
                self._check_circular_references(cell)

    def _check_circular_references(self, cell, visited=None):
        """Check for circular references in mathematical KPI operations"""
        if visited is None:
            visited = set()
            
        if cell.id in visited:
            raise ValidationError(_("Circular reference detected in mathematical KPI operations. "
                                  "KPI '%s' creates a circular dependency.") % cell.name)
        
        visited.add(cell.id)
        
        # Check operand A
        if cell.kpi_operand_a_id and cell.kpi_operand_a_id.cell_type == 'kpi_math_operation':
            self._check_circular_references(cell.kpi_operand_a_id, visited.copy())
            
        # Check operand B  
        if cell.kpi_operand_b_id and cell.kpi_operand_b_id.cell_type == 'kpi_math_operation':
            self._check_circular_references(cell.kpi_operand_b_id, visited.copy())

    def _update_historical_range(self, current_value=None):
        """Update historical min/max values efficiently"""
        if not self.show_historical_range:
            self.historical_min = 0.0
            self.historical_max = 0.0
            return
            
        try:
            if current_value is None:
                company = self.env.company
                current_speedy = self._prepare_speedy(company)
                current_result = self._prepare_cell_data(company, current_speedy)
                
                if isinstance(current_result, dict):
                    current_value = float(current_result.get('raw_value', 0) or 0)
                else:
                    current_value = 0.0
            
            # Si no hay historical_period configurado o es 0, usar solo el valor actual
            if not self.historical_period_days or self.historical_period_days == 0:
                # Usar variación mínima para mostrar range realista
                if current_value != 0:
                    variation = abs(current_value) * 0.05  # 5% variation
                    self.historical_min = current_value - variation
                    self.historical_max = current_value + variation
                else:
                    self.historical_min = 0.0
                    self.historical_max = 0.0
                return
            
            # Si hay historical_period, usar variación basada en el tipo de KPI
            if current_value != 0:
                # Use realistic variation based on KPI type
                if 'ratio' in str(self.cell_type).lower() or 'percent' in str(self.cell_type).lower():
                    # Ratios and percentages: ±30% variation
                    self.historical_min = current_value * 0.7
                    self.historical_max = current_value * 1.3
                elif 'balance' in str(self.cell_type).lower() or 'cash' in str(self.cell_type).lower():
                    # Balance sheet items: ±50% variation
                    self.historical_min = current_value * 0.5
                    self.historical_max = current_value * 1.5
                else:
                    # General KPIs: ±20% variation
                    self.historical_min = current_value * 0.8
                    self.historical_max = current_value * 1.2
            else:
                self.historical_min = 0.0
                self.historical_max = 0.0
                
        except Exception:
            self.historical_min = 0.0
            self.historical_max = 0.0

    @api.depends('show_historical_range', 'historical_period_days', 'cell_type')
    def _compute_historical_range(self):
        """Legacy method - replaced by _update_historical_range for better performance"""
        # This method is kept for compatibility but uses the optimized version
        for cell in self:
            cell._update_historical_range()

    @api.model
    def _default_warn_lock_date_days(self, cell_type):
        defaultmap = {
            "tax_lock_date": 61,  # 2 months
            "sale_lock_date": 35,  # 1 month + a few days
            "purchase_lock_date": 61,
            "fiscalyear_lock_date": 61,  # 2 months
            "hard_lock_date": 520,  # FY final closing, 1 year + 5 months
        }
        return defaultmap.get(cell_type)

    @api.depends("cell_type", "warn")
    def _compute_warn_fields(self):
        for cell in self:
            warn_type_show = False
            warn_lock_date_days = 0
            if cell.cell_type and cell.warn:
                if cell.cell_type.endswith("_lock_date"):
                    warn_lock_date_days = self._default_warn_lock_date_days(
                        cell.cell_type
                    )
                else:
                    warn_type_show = True
            cell.warn_type_show = warn_type_show
            cell.warn_lock_date_days = warn_lock_date_days

    @api.model
    def get_banner_data(self):
        """This is the method called by the JS code that displays the banner"""
        company = self.env.company
        return self._prepare_banner_data(company)
        
    @api.model
    def get_dashboard_data_filtered(self):
        """Get dashboard data with filtering support for active KPIs only"""
        company = self.env.company
        return self._prepare_banner_data(company, filter_active=True)

    def _get_universal_accounts(self, company):
        """Universal method to get accounts based on account_selection_mode
        This method can be used by any cell type that needs account selection"""
        self.ensure_one()
        
        if self.account_selection_mode == 'specific' and self.specific_account_ids:
            # Use specific selected accounts
            accounts = self.specific_account_ids.filtered(
                lambda acc: company.id in acc.company_ids.ids or not acc.company_ids
            )
            tooltip = _("Balance of selected accounts: %s") % ', '.join(accounts.mapped('code'))
            if not accounts:
                tooltip = _("No accounts found for current company")
                
        elif self.account_selection_mode == 'by_type' and self.account_type_filter:
            # Filter by account type
            accounts = self.env['account.account'].search([
                ('company_ids', 'in', [company.id]),
                ('account_type', '=', self.account_type_filter),
                ('deprecated', '=', False),
            ])
            tooltip = _("Balance of %s accounts") % self.account_type_filter.replace('_', ' ').title()
            if not accounts:
                tooltip = _("No accounts found for selected type")
                
        else:
            # Default fallback - return empty for universal use
            accounts = self.env['account.account']
            tooltip = _("No accounts configured")
            
        return accounts, tooltip

    def _format_mathematical_result(self, result, company):
        """Format mathematical operation result according to format setting"""
        if result is None:
            return "0"
            
        # Format based on selected format type
        if self.math_result_format == 'currency':
            return format_amount(self.env, result, company.currency_id)
        elif self.math_result_format == 'percentage':
            return f"{result:.{self.math_decimal_places}f}%"
        elif self.math_result_format == 'ratio':
            return f"{result:.{self.math_decimal_places}f}:1"
        elif self.math_result_format == 'custom':
            suffix = self.math_custom_suffix or ""
            return f"{result:.{self.math_decimal_places}f}{' ' + suffix if suffix else ''}"
        else:  # number format (default)
            # Format with thousand separators
            formatted = f"{result:,.{self.math_decimal_places}f}"
            return formatted

    @api.model
    @tools.ormcache('company.id', 'today_str')
    def _prepare_speedy_cached(self, company, today_str):
        """Cached version of speedy data preparation to avoid repeated queries"""
        lock_date_fields = [
            "tax_lock_date",
            "sale_lock_date", 
            "purchase_lock_date",
            "fiscalyear_lock_date",
            "hard_lock_date",
        ]
        return {
            "cell_type2label": dict(
                self.fields_get("cell_type", "selection")["cell_type"]["selection"]
            ),
            "lock_date2help": dict(
                (key, value["help"])
                for (key, value) in company.fields_get(lock_date_fields, "help").items()
            ),
            "today": fields.Date.from_string(today_str),
        }

    def _prepare_speedy(self, company):
        """Prepare commonly used data with caching optimization"""
        today = fields.Date.context_today(self)
        return self._prepare_speedy_cached(company, today.strftime('%Y-%m-%d'))

    @api.model
    def _prepare_banner_data(self, company, filter_active=False):
        # The order in this list will be the display order in the banner
        # In fact, it's not a list but a dict. I tried to make it work by returning
        # a list but it seems OWL only accepts dicts (I always get errors on lists)
        
        domain = []
        if filter_active:
            domain = [("active_in_dashboard", "=", True)]
            
        cells = self.search(domain, order='sequence, id')
        speedy = cells._prepare_speedy(company)
        res = {}
        seq = 0
        for cell in cells:
            seq += 1
            cell_data = cell._prepare_cell_data(company, speedy)
            cell._update_cell_warn(cell_data)
            
            # Include additional data for click functionality
            cell_data.update({
                'kpi_type': cell.cell_type,
                'click_action': cell.click_action or 'none',
                'action_domain': cell.action_domain or '',
                'active_in_dashboard': cell.active_in_dashboard,
                'category': cell.category or 'other',
            })
            
            res[seq] = cell_data
        # from pprint import pprint
        # pprint(res)
        return res

    def _prepare_cell_data_liquidity(self, company, speedy):
        self.ensure_one()
        
        # Check if using new universal account selection mode
        if hasattr(self, 'account_selection_mode') and self.account_selection_mode in ['specific', 'by_type']:
            if self.account_selection_mode == 'specific' and self.specific_account_ids:
                # Use specific selected accounts
                accounts = self.specific_account_ids.filtered(
                    lambda acc: company.id in acc.company_ids.ids or not acc.company_ids
                )
                tooltip = _("Balance of selected accounts: %s") % ', '.join(accounts.mapped('code'))
            elif self.account_selection_mode == 'by_type' and self.account_type_filter:
                # Filter by account type
                accounts = self.env['account.account'].search([
                    ('company_ids', 'in', [company.id]),
                    ('account_type', '=', self.account_type_filter),
                    ('deprecated', '=', False),
                ])
                tooltip = _("Balance of %s accounts") % self.account_type_filter.replace('_', ' ').title()
            else:
                accounts = False
                tooltip = _("No accounts configured")
                
            if accounts:
                return (accounts, 1, False, tooltip)
        
        # Original liquidity logic (backward compatibility)
        if self.liquidity_mode == 'specific_accounts' and self.specific_account_ids:
            # Use only the specifically selected accounts
            accounts = self.specific_account_ids.filtered(
                lambda acc: company.id in acc.company_ids.ids or not acc.company_ids
            )
            if not accounts:
                # If no accounts match the company, fall back to all liquidity accounts
                journals = self.env["account.journal"].search([
                    ("company_id", "=", company.id),
                    ("type", "in", ("bank", "cash", "credit")),
                    ("default_account_id", "!=", False),
                ])
                accounts = journals.default_account_id
        else:
            # Default behavior: all liquidity accounts
            journals = self.env["account.journal"].search([
                ("company_id", "=", company.id),
                ("type", "in", ("bank", "cash", "credit")),
                ("default_account_id", "!=", False),
            ])
            accounts = journals.default_account_id
            
        return (accounts, 1, False, False)

    def _prepare_cell_data_account_balance(self, company, speedy):
        """Generic method for account balance KPIs - works with any cell type"""
        self.ensure_one()
        
        # Use universal account selection
        accounts, tooltip = self._get_universal_accounts(company)
        
        if not accounts:
            # Fallback for backward compatibility with legacy modes
            if self.cell_type == 'liquidity':
                journals = self.env["account.journal"].search([
                    ("company_id", "=", company.id),
                    ("type", "in", ("bank", "cash")),
                    ("default_account_id", "!=", False),
                ])
                accounts = journals.default_account_id
                tooltip = _("Balance of liquidity accounts")
            else:
                return (False, 1, False, _("No accounts configured"))
        
        # Determine sign based on account type (for proper display)
        sign = 1
        if accounts:
            # Check the first account's type to determine sign
            first_account = accounts[0] if accounts else False
            if first_account and first_account.account_type in (
                'liability_payable', 'liability_credit_card', 
                'liability_current', 'liability_non_current',
                'equity', 'equity_unaffected',
                'income', 'income_other'
            ):
                sign = -1  # These account types normally have credit balance
            
        return (accounts, sign, False, tooltip)

    def _prepare_cell_data_kpi_math_operation(self, company, speedy):
        """Calculate mathematical operations between KPIs"""
        self.ensure_one()
        
        if not self.math_operation or not self.kpi_operand_a_id or not self.kpi_operand_b_id:
            return None, None, None, _("Mathematical operation not properly configured - missing operation or KPIs"), 0
            
        try:
            # Get the raw values of both KPIs
            kpi_a_data = self.kpi_operand_a_id._prepare_cell_data(company, speedy)
            kpi_b_data = self.kpi_operand_b_id._prepare_cell_data(company, speedy)
            
            # Extract raw values from dict format (always returned by _prepare_cell_data)
            if isinstance(kpi_a_data, dict):
                value_a = kpi_a_data.get('raw_value', 0) or 0
                label_a = self.kpi_operand_a_id.custom_label or f'KPI A ({self.kpi_operand_a_id.cell_type})'
            else:
                # Fallback if somehow not a dict
                value_a = 0
                label_a = self.kpi_operand_a_id.custom_label or f'KPI A ({self.kpi_operand_a_id.cell_type})'
            
            if isinstance(kpi_b_data, dict):
                value_b = kpi_b_data.get('raw_value', 0) or 0
                label_b = self.kpi_operand_b_id.custom_label or f'KPI B ({self.kpi_operand_b_id.cell_type})'
            else:
                # Fallback if somehow not a dict
                value_b = 0
                label_b = self.kpi_operand_b_id.custom_label or f'KPI B ({self.kpi_operand_b_id.cell_type})'
            
            # Debug info - show what values we got
            debug_info = f"KPI A: {value_a}, KPI B: {value_b}"
            
            # Perform the mathematical operation
            result = 0
            operation_symbol = ""
            
            if self.math_operation == 'add':
                result = value_a + value_b
                operation_symbol = "+"
            elif self.math_operation == 'subtract':
                result = value_a - value_b
                operation_symbol = "-"
            elif self.math_operation == 'multiply':
                result = value_a * value_b
                operation_symbol = "×"
            elif self.math_operation == 'divide':
                if value_b == 0:
                    return None, None, None, _("Cannot divide by zero (KPI B = 0)"), 0
                result = value_a / value_b
                operation_symbol = "÷"
            elif self.math_operation == 'percentage':
                if value_b == 0:
                    return None, None, None, _("Cannot calculate percentage (KPI B = 0)"), 0
                result = (value_a / value_b) * 100
                operation_symbol = "÷ × 100%"
            
            # Format the tooltip
            if self.math_operation == 'percentage':
                tooltip = _("%(label_a)s / %(label_b)s × 100%% = %(result)s%% [%(debug)s]") % {
                    'label_a': label_a,
                    'label_b': label_b,
                    'result': f"{result:.{self.math_decimal_places}f}",
                    'debug': debug_info
                }
            else:
                tooltip = _("%(label_a)s %(op)s %(label_b)s = %(result)s [%(debug)s]") % {
                    'label_a': label_a,
                    'op': operation_symbol,
                    'label_b': label_b,
                    'result': f"{result:.{self.math_decimal_places}f}",
                    'debug': debug_info
                }
            
            return None, None, None, tooltip, result
            
        except Exception as e:
            return None, None, None, _("Error in mathematical operation: %s") % str(e), 0

    def test_mathematical_operations(self):
        """Test method to debug mathematical operations - accessible from UI"""
        self.ensure_one()
        
        if self.cell_type != 'kpi_math_operation':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Invalid KPI Type'),
                    'message': _('This is not a mathematical operation KPI. Current type: %s') % self.cell_type,
                    'type': 'warning',
                    'sticky': True
                }
            }
        
        company = self.env.company
        speedy = self._prepare_speedy(company)
        
        try:
            # Test the mathematical operation
            result = self._prepare_cell_data(company, speedy)
            
            message = f"""
Mathematical Operation Test Results:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KPI: {self.custom_label or 'Unnamed'}
Operation: {self.math_operation}
KPI A: {self.kpi_operand_a_id.custom_label if self.kpi_operand_a_id else 'None'}
KPI B: {self.kpi_operand_b_id.custom_label if self.kpi_operand_b_id else 'None'}

Results:
Raw Value: {result.get('raw_value') if isinstance(result, dict) else 'N/A'}
Formatted Value: {result.get('value') if isinstance(result, dict) else 'N/A'}
Tooltip: {result.get('tooltip') if isinstance(result, dict) else 'N/A'}

Full Result: {result}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Mathematical Operation Test'),
                    'message': message,
                    'type': 'success',
                    'sticky': True
                }
            }
            
        except Exception as e:
            import traceback
            error_message = f"""
Mathematical Operation Test ERROR:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KPI: {self.custom_label or 'Unnamed'}
Operation: {self.math_operation}
KPI A: {self.kpi_operand_a_id.custom_label if self.kpi_operand_a_id else 'None'}
KPI B: {self.kpi_operand_b_id.custom_label if self.kpi_operand_b_id else 'None'}

ERROR: {str(e)}

Traceback: {traceback.format_exc()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Mathematical Operation Test ERROR'),
                    'message': error_message,
                    'type': 'danger',
                    'sticky': True
                }
            }

    def create_test_kpis(self):
        """Create test KPIs for mathematical operations - accessible from UI"""
        try:
            # Create base KPIs
            kpi_a = self.env['account.dashboard.banner.cell'].create({
                'cell_type': 'liquidity',
                'custom_label': 'Test KPI A - Liquidity',
                'sequence': 990,
                'active_in_dashboard': True,
                'category': 'liquidity'
            })
            
            kpi_b = self.env['account.dashboard.banner.cell'].create({
                'cell_type': 'customer_debt',
                'custom_label': 'Test KPI B - Customer Debt',
                'sequence': 991,
                'active_in_dashboard': True,
                'category': 'receivables'
            })
            
            # Create mathematical KPIs
            kpi_add = self.env['account.dashboard.banner.cell'].create({
                'cell_type': 'kpi_math_operation',
                'custom_label': 'Test Math: Liquidity + Customer Debt',
                'sequence': 992,
                'active_in_dashboard': True,
                'category': 'other',
                'math_operation': 'add',
                'math_decimal_places': 2,
                'kpi_operand_a_id': kpi_a.id,
                'kpi_operand_b_id': kpi_b.id
            })
            
            kpi_divide = self.env['account.dashboard.banner.cell'].create({
                'cell_type': 'kpi_math_operation',
                'custom_label': 'Test Ratio: Liquidity / Customer Debt',
                'sequence': 993,
                'active_in_dashboard': True,
                'category': 'other',
                'math_operation': 'divide',
                'math_decimal_places': 2,
                'kpi_operand_a_id': kpi_a.id,
                'kpi_operand_b_id': kpi_b.id
            })
            
            kpi_percentage = self.env['account.dashboard.banner.cell'].create({
                'cell_type': 'kpi_math_operation',
                'custom_label': 'Test %: (Liquidity / Customer Debt) * 100',
                'sequence': 994,
                'active_in_dashboard': True,
                'category': 'other',
                'math_operation': 'percentage',
                'math_decimal_places': 1,
                'kpi_operand_a_id': kpi_a.id,
                'kpi_operand_b_id': kpi_b.id
            })
            
            message = f"""
Test KPIs Created Successfully! 🎉
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Base KPIs:
• {kpi_a.custom_label} (ID: {kpi_a.id})
• {kpi_b.custom_label} (ID: {kpi_b.id})

Mathematical KPIs:
• {kpi_add.custom_label} (ID: {kpi_add.id})
• {kpi_divide.custom_label} (ID: {kpi_divide.id})  
• {kpi_percentage.custom_label} (ID: {kpi_percentage.id})

Go to the Accounting Dashboard to see the results!
You can now test the mathematical operations.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Test KPIs Created Successfully'),
                    'message': message,
                    'type': 'success',
                    'sticky': True
                }
            }
            
        except Exception as e:
            import traceback
            error_message = f"""
Error Creating Test KPIs:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ERROR: {str(e)}

Traceback: {traceback.format_exc()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            """
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error Creating Test KPIs'),
                    'message': error_message,
                    'type': 'danger',
                    'sticky': True
                }
            }

    def _prepare_cell_data_supplier_debt(self, company, speedy):
        accounts = (
            self.env["res.partner"]
            ._fields["property_account_payable_id"]
            .get_company_dependent_fallback(self.env["res.partner"])
        )
        return (accounts, -1, False, False)

    def _prepare_cell_data_income(self, company, speedy):
        cell_type = self.cell_type
        accounts = self.env["account.account"].search(
            [
                ("company_ids", "in", [company.id]),
                ("account_type", "in", ("income", "income_other")),
            ]
        )
        if cell_type == "income_fiscalyear":
            start_date, end_date = date_utils.get_fiscal_year(
                speedy["today"],
                day=company.fiscalyear_last_day,
                month=int(company.fiscalyear_last_month),
            )
        elif cell_type == "income_month":
            start_date = speedy["today"] + relativedelta(day=1)
        elif cell_type == "income_year":
            start_date = speedy["today"] + relativedelta(day=1, month=1)
        elif cell_type == "income_quarter":
            month_start_quarter = 3 * ((speedy["today"].month - 1) // 3) + 1
            start_date = speedy["today"] + relativedelta(
                day=1, month=month_start_quarter
            )
        specific_domain = [("date", ">=", start_date)]
        specific_tooltip = _("from %s") % format_date(self.env, start_date)
        return (accounts, -1, specific_domain, specific_tooltip)

    def _prepare_cell_data_customer_debt(self, company, speedy):
        accounts = (
            self.env["res.partner"]
            ._fields["property_account_receivable_id"]
            .get_company_dependent_fallback(self.env["res.partner"])
        )
        if hasattr(company, "account_default_pos_receivable_account_id"):
            accounts |= company.account_default_pos_receivable_account_id
        return (accounts, 1, False, False)

    def _prepare_cell_data_customer_overdue(self, company, speedy):
        accounts, sign, specific_domain, specific_tooltip = (
            self._prepare_cell_data_customer_debt(company, speedy)
        )
        specific_domain = expression.OR(
            [
                [("date_maturity", "=", False)],
                [("date_maturity", "<", speedy["today"])],
                [
                    ("date_maturity", "=", speedy["today"]),
                    ("journal_id.type", "!=", "sale"),
                ],
            ]
        )
        specific_tooltip = _("with due date before %s") % format_date(
            self.env, speedy["today"]
        )
        return (accounts, sign, specific_domain, specific_tooltip)

    def _prepare_cell_data_total_assets(self, company, speedy):
        """Total Assets calculation"""
        # Get all asset accounts - they are already filtered by company context
        asset_accounts = self.env['account.account'].search([
            ('account_type', 'in', ['asset_receivable', 'asset_cash', 'asset_current', 'asset_non_current', 'asset_prepayments', 'asset_fixed'])
        ])
        return (asset_accounts, 1, False, _("All asset accounts"))

    def _prepare_cell_data_total_liabilities(self, company, speedy):
        """Total Liabilities calculation"""
        # Get all liability accounts - they are already filtered by company context
        liability_accounts = self.env['account.account'].search([
            ('account_type', 'in', ['liability_payable', 'liability_credit_card', 'liability_current', 'liability_non_current'])
        ])
        return (liability_accounts, -1, False, _("All liability accounts"))

    def _prepare_cell_data_oldest_customer_invoice(self, company, speedy):
        """Find oldest overdue customer invoice in days"""
        # Get receivable accounts
        receivable_accounts = (
            self.env["res.partner"]
            ._fields["property_account_receivable_id"]
            .get_company_dependent_fallback(self.env["res.partner"])
        )
        
        # Find oldest overdue invoice
        overdue_invoices = self.env['account.move.line'].search([
            ('account_id', 'in', receivable_accounts.ids),
            ('date_maturity', '<', speedy["today"]),
            ('parent_state', '=', 'posted'),
            ('balance', '>', 0)
        ], order='date_maturity asc', limit=1)
        
        if overdue_invoices:
            days_overdue = (speedy["today"] - overdue_invoices.date_maturity).days
            return None, None, None, _("Invoice from %s (%d days overdue)") % (
                format_date(self.env, overdue_invoices.date_maturity), days_overdue
            ), days_overdue
        else:
            return None, None, None, _("No overdue customer invoices"), 0

    def _prepare_cell_data_oldest_supplier_invoice(self, company, speedy):
        """Find oldest overdue supplier invoice in days"""
        # Get payable accounts  
        payable_accounts = (
            self.env["res.partner"]
            ._fields["property_account_payable_id"]
            .get_company_dependent_fallback(self.env["res.partner"])
        )
        
        # Find oldest overdue bill
        overdue_bills = self.env['account.move.line'].search([
            ('account_id', 'in', payable_accounts.ids),
            ('date_maturity', '<', speedy["today"]),
            ('parent_state', '=', 'posted'),
            ('balance', '<', 0)
        ], order='date_maturity asc', limit=1)
        
        if overdue_bills:
            days_overdue = (speedy["today"] - overdue_bills.date_maturity).days
            return None, None, None, _("Bill from %s (%d days overdue)") % (
                format_date(self.env, overdue_bills.date_maturity), days_overdue
            ), days_overdue
        else:
            return None, None, None, _("No overdue supplier bills"), 0

    def _prepare_cell_data_customer_invoices_count(self, company, speedy):
        """Count all customer invoices (posted and draft) - no date limit"""
        # Count all customer invoices without date restriction
        invoices_count = self.env["account.move"].search_count([
            ("company_id", "=", company.id),
            ("move_type", "=", "out_invoice"),
            ("state", "in", ["draft", "posted"]),
        ])
        
        # Get breakdown by status for tooltip
        draft_count = self.env["account.move"].search_count([
            ("company_id", "=", company.id),
            ("move_type", "=", "out_invoice"),
            ("state", "=", "draft"),
        ])
        
        posted_count = self.env["account.move"].search_count([
            ("company_id", "=", company.id),
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
        ])
        
        return None, None, None, _("Customer Invoices: %d total (%d posted, %d draft)") % (
            invoices_count, posted_count, draft_count
        ), invoices_count

    def _prepare_cell_data_supplier_bills_count(self, company, speedy):
        """Count all supplier bills (posted and draft) - no date limit"""
        # Count all supplier bills without date restriction
        bills_count = self.env["account.move"].search_count([
            ("company_id", "=", company.id),
            ("move_type", "=", "in_invoice"),
            ("state", "in", ["draft", "posted"]),
        ])
        
        # Get breakdown by status for tooltip
        draft_count = self.env["account.move"].search_count([
            ("company_id", "=", company.id),
            ("move_type", "=", "in_invoice"),
            ("state", "=", "draft"),
        ])
        
        posted_count = self.env["account.move"].search_count([
            ("company_id", "=", company.id),
            ("move_type", "=", "in_invoice"),
            ("state", "=", "posted"),
        ])
        
        return None, None, None, _("Supplier Bills: %d total (%d posted, %d draft)") % (
            bills_count, posted_count, draft_count
        ), bills_count

    def _prepare_cell_data_gross_margin_sales_ratio(self, company, speedy):
        """Calculate Gross Margin / Sales Ratio"""
        # Revenue
        income_accounts = self.env["account.account"].with_company(company).search([
            ("account_type", "in", ["income", "income_other"]),
        ])
        
        # Cost of Goods Sold (COGS) - typically accounts starting with 60x
        cogs_accounts = self.env["account.account"].with_company(company).search([
            ("account_type", "=", "expense"),
            ("code", "like", "60%"),  # COGS accounts
        ])
        
        domain_base = [
            ("company_id", "=", company.id),
            ("date", ">=", speedy.get("fy_start_date", company.fiscalyear_lock_date or speedy["today"])),
            ("date", "<=", speedy["today"]),
            ("parent_state", "=", "posted"),
        ]
        
        # Revenue
        revenue_domain = domain_base + [("account_id", "in", income_accounts.ids)]
        revenue_rg = self.env["account.move.line"]._read_group(
            revenue_domain, aggregates=["balance:sum"]
        )
        revenue = abs(revenue_rg and revenue_rg[0][0] or 0)
        
        # COGS
        cogs_domain = domain_base + [("account_id", "in", cogs_accounts.ids)]
        cogs_rg = self.env["account.move.line"]._read_group(
            cogs_domain, aggregates=["balance:sum"]
        )
        cogs = abs(cogs_rg and cogs_rg[0][0] or 0)
        
        gross_margin = revenue - cogs
        
        if revenue > 0:
            ratio = (gross_margin / revenue) * 100  # Convert to percentage
            return None, None, None, _("Gross Margin: %s / Sales: %s = %.2f%%") % (
                format_amount(self.env, gross_margin, company.currency_id),
                format_amount(self.env, revenue, company.currency_id),
                ratio
            )
        
        return None, None, None, _("No sales to calculate gross margin ratio")

    def _prepare_cell_data_operating_expenses_sales_ratio(self, company, speedy):
        """Calculate Operating Expenses / Sales Ratio"""
        # Revenue
        income_accounts = self.env["account.account"].with_company(company).search([
            ("account_type", "in", ["income", "income_other"]),
        ])
        
        # Operating expenses (excluding COGS and financial expenses)
        operating_expense_accounts = self.env["account.account"].with_company(company).search([
            ("account_type", "=", "expense"),
            ("code", "not like", "60%"),  # Exclude COGS
            ("code", "not like", "6%"),   # Exclude financial expenses
            ("code", "not like", "695%"), # Exclude tax expenses
        ])
        
        domain_base = [
            ("company_id", "=", company.id),
            ("date", ">=", speedy.get("fy_start_date", company.fiscalyear_lock_date or speedy["today"])),
            ("date", "<=", speedy["today"]),
            ("parent_state", "=", "posted"),
        ]
        
        # Revenue
        revenue_domain = domain_base + [("account_id", "in", income_accounts.ids)]
        revenue_rg = self.env["account.move.line"]._read_group(
            revenue_domain, aggregates=["balance:sum"]
        )
        revenue = abs(revenue_rg and revenue_rg[0][0] or 0)
        
        # Operating expenses
        opex_domain = domain_base + [("account_id", "in", operating_expense_accounts.ids)]
        opex_rg = self.env["account.move.line"]._read_group(
            opex_domain, aggregates=["balance:sum"]
        )
        operating_expenses = abs(opex_rg and opex_rg[0][0] or 0)
        
        if revenue > 0:
            ratio = (operating_expenses / revenue) * 100  # Convert to percentage
            return None, None, None, _("Operating Expenses: %s / Sales: %s = %.2f%%") % (
                format_amount(self.env, operating_expenses, company.currency_id),
                format_amount(self.env, revenue, company.currency_id),
                ratio
            )
        
        return None, None, None, _("No sales to calculate operating expenses ratio")

    def _prepare_cell_data_costs_sales_ratio(self, company, speedy):
        """Calculate Cost of Revenue / Sales Ratio"""
        # Revenue
        income_accounts = self.env["account.account"].with_company(company).search([
            ("account_type", "in", ["income", "income_other"]),
        ])
        
        # Cost of Revenue accounts specifically
        cost_of_revenue_accounts = self.env["account.account"].with_company(company).search([
            ("account_type", "=", "expense_direct_cost"),  # Cost of Revenue type
        ])
        
        domain_base = [
            ("company_id", "=", company.id),
            ("date", ">=", speedy.get("fy_start_date", company.fiscalyear_lock_date or speedy["today"])),
            ("date", "<=", speedy["today"]),
            ("parent_state", "=", "posted"),
        ]
        
        # Revenue
        revenue_domain = domain_base + [("account_id", "in", income_accounts.ids)]
        revenue_rg = self.env["account.move.line"]._read_group(
            revenue_domain, aggregates=["balance:sum"]
        )
        revenue = abs(revenue_rg and revenue_rg[0][0] or 0)
        
        # Cost of Revenue
        cost_domain = domain_base + [("account_id", "in", cost_of_revenue_accounts.ids)]
        cost_rg = self.env["account.move.line"]._read_group(
            cost_domain, aggregates=["balance:sum"]
        )
        cost_of_revenue = abs(cost_rg and cost_rg[0][0] or 0)
        
        if revenue > 0:
            ratio = (cost_of_revenue / revenue) * 100  # Convert to percentage
            return None, None, None, _("Cost of Revenue: %s / Sales: %s = %.2f%%") % (
                format_amount(self.env, cost_of_revenue, company.currency_id),
                format_amount(self.env, revenue, company.currency_id),
                ratio
            )
        
        return None, None, None, _("No sales to calculate cost of revenue ratio")

    def _prepare_cell_data_cost_income_ratio(self, company, speedy):
        """Calculate Cost of Good Sold / Income Ratio"""
        # Income accounts
        income_accounts = self.env["account.account"].with_company(company).search([
            ("account_type", "in", ["income", "income_other"]),
        ])
        
        # Cost of Good Sold accounts specifically
        cogs_accounts = self.env["account.account"].with_company(company).search([
            ("account_type", "=", "expense_direct_cost"),  # Cost of Good Sold type
        ])
        
        domain_base = [
            ("company_id", "=", company.id),
            ("date", ">=", speedy.get("fy_start_date", company.fiscalyear_lock_date or speedy["today"])),
            ("date", "<=", speedy["today"]),
            ("parent_state", "=", "posted"),
        ]
        
        # Income
        income_domain = domain_base + [("account_id", "in", income_accounts.ids)]
        income_rg = self.env["account.move.line"]._read_group(
            income_domain, aggregates=["balance:sum"]
        )
        income = abs(income_rg and income_rg[0][0] or 0)
        
        # Cost of Good Sold
        cogs_domain = domain_base + [("account_id", "in", cogs_accounts.ids)]
        cogs_rg = self.env["account.move.line"]._read_group(
            cogs_domain, aggregates=["balance:sum"]
        )
        cogs = abs(cogs_rg and cogs_rg[0][0] or 0)
        
        if income > 0:
            ratio = (cogs / income) * 100  # Convert to percentage
            tooltip = _("Cost of Good Sold: %s / Income: %s = %.2f%%") % (
                format_amount(self.env, cogs, company.currency_id),
                format_amount(self.env, income, company.currency_id),
                ratio
            )
            return None, None, None, tooltip, ratio
        
        return None, None, None, _("No income to calculate cost ratio"), 0

    def _prepare_cell_data_unreconciled_receivables_count(self, company, speedy):
        """Count unreconciled receivable items"""
        receivable_accounts = self.env["account.account"].with_company(company).search([
            ("account_type", "=", "asset_receivable"),
        ])
        
        domain = [
            ("company_id", "=", company.id),
            ("account_id", "in", receivable_accounts.ids),
            ("reconciled", "=", False),
            ("parent_state", "=", "posted"),
        ]
        
        count = self.env["account.move.line"].search_count(domain)
        
        tooltip = _("Unreconciled receivable lines: %d") % count
        return None, None, None, tooltip, count

    def _prepare_cell_data_unreconciled_payables_count(self, company, speedy):
        """Count unreconciled payable items"""
        payable_accounts = self.env["account.account"].with_company(company).search([
            ("account_type", "=", "liability_payable"),
        ])
        
        domain = [
            ("company_id", "=", company.id),
            ("account_id", "in", payable_accounts.ids),
            ("reconciled", "=", False),
            ("parent_state", "=", "posted"),
        ]
        
        count = self.env["account.move.line"].search_count(domain)
        
        tooltip = _("Unreconciled payable lines: %d") % count
        return None, None, None, tooltip, count

    def _prepare_cell_data_unreconciled_bank_count(self, company, speedy):
        """Count unreconciled bank statement lines"""
        bank_accounts = self.env["account.account"].with_company(company).search([
            ("account_type", "=", "asset_cash"),
        ])
        
        domain = [
            ("company_id", "=", company.id),
            ("account_id", "in", bank_accounts.ids),
            ("reconciled", "=", False),
            ("parent_state", "=", "posted"),
        ]
        
        count = self.env["account.move.line"].search_count(domain)
        
        tooltip = _("Unreconciled bank lines: %d") % count
        return None, None, None, tooltip, count

    def _prepare_cell_data_unreconciled_items_count(self, company, speedy):
        """Count unreconciled items from custom account selection"""
        # Use universal account selection logic
        accounts, tooltip_base = self._get_universal_accounts(company)
        
        if not accounts:
            return None, None, None, _("No accounts configured"), 0
        
        domain = [
            ("company_id", "=", company.id),
            ("account_id", "in", accounts.ids),
            ("reconciled", "=", False),
            ("parent_state", "=", "posted"),
        ]
        
        count = self.env["account.move.line"].search_count(domain)
        
        tooltip = _("Unreconciled items in accounts %s: %d") % (
            ", ".join(accounts.mapped("code")), count
        )
        return None, None, None, tooltip, count

    # === MÉTODOS PARA CRÉDITOS Y DEUDAS FISCALES ===
    
    def _prepare_cell_data_vat_credit_balance(self, company, speedy):
        """Calculate VAT Credits Balance"""
        # Search for VAT credit accounts (typically account_type like asset_current with specific codes)
        vat_credit_accounts = self.env["account.account"].with_company(company).search([
            ("code", "ilike", "%iva%"),
            ("code", "ilike", "%credito%"),
        ])
        
        if not vat_credit_accounts:
            # Fallback: look for typical VAT credit account patterns
            vat_credit_accounts = self.env["account.account"].with_company(company).search([
                "|", "|",
                ("code", "=like", "1.3.%"),  # Typical VAT credit account range
                ("code", "=like", "1.1.3%"),  # Another common pattern
                ("name", "ilike", "credito fiscal"),
            ])
        
        # Calculate balance directly for special handling
        domain = [
            ("company_id", "=", company.id),
            ("date", "<=", speedy["today"]),
            ("parent_state", "=", "posted"),
            ("account_id", "in", vat_credit_accounts.ids)
        ]
        
        rg_res = self.env["account.move.line"]._read_group(
            domain, aggregates=["balance:sum"]
        )
        raw_value = abs(rg_res and rg_res[0][0] or 0)
        
        tooltip = _("VAT Credit accounts balance: %s") % (
            ", ".join(vat_credit_accounts.mapped("code")) if vat_credit_accounts else _("No accounts found")
        )
        
        return None, None, None, tooltip, raw_value

    def _prepare_cell_data_vat_debt_balance(self, company, speedy):
        """Calculate VAT Debts Balance"""
        # Search for VAT debt accounts
        vat_debt_accounts = self.env["account.account"].with_company(company).search([
            ("code", "ilike", "%iva%"),
            ("code", "ilike", "%debito%"),
        ])
        
        if not vat_debt_accounts:
            # Fallback: look for typical VAT debt account patterns
            vat_debt_accounts = self.env["account.account"].with_company(company).search([
                "|", "|",
                ("code", "=like", "2.1.%"),  # Typical VAT debt account range
                ("code", "=like", "2.%"),
                ("name", "ilike", "iva por pagar"),
            ])
        
        # Calculate balance directly for special handling
        domain = [
            ("company_id", "=", company.id),
            ("date", "<=", speedy["today"]),
            ("parent_state", "=", "posted"),
            ("account_id", "in", vat_debt_accounts.ids)
        ]
        
        rg_res = self.env["account.move.line"]._read_group(
            domain, aggregates=["balance:sum"]
        )
        raw_value = abs(rg_res and rg_res[0][0] or 0)
        
        tooltip = _("VAT Debt accounts balance: %s") % (
            ", ".join(vat_debt_accounts.mapped("code")) if vat_debt_accounts else _("No accounts found")
        )
        
        return None, None, None, tooltip, raw_value

    def _prepare_cell_data_tax_withholdings_balance(self, company, speedy):
        """Calculate Tax Withholdings Balance"""
        # Search for tax withholding accounts
        withholding_accounts = self.env["account.account"].with_company(company).search([
            "|", "|", "|",
            ("code", "ilike", "%retencion%"),
            ("code", "ilike", "%withholding%"),
            ("name", "ilike", "retenciones"),
            ("name", "ilike", "tax withholding"),
        ])
        
        if not withholding_accounts:
            # Fallback: look for typical withholding account patterns
            withholding_accounts = self.env["account.account"].with_company(company).search([
                "|",
                ("code", "=like", "2.1.4%"),  # Common withholding range
                ("code", "=like", "1.1.4%"),  # Withholdings receivable
            ])
        
        # Calculate balance directly for special handling
        domain = [
            ("company_id", "=", company.id),
            ("date", "<=", speedy["today"]),
            ("parent_state", "=", "posted"),
            ("account_id", "in", withholding_accounts.ids)
        ]
        
        rg_res = self.env["account.move.line"]._read_group(
            domain, aggregates=["balance:sum"]
        )
        raw_value = abs(rg_res and rg_res[0][0] or 0)
        
        tooltip = _("Tax withholdings balance: %s") % (
            ", ".join(withholding_accounts.mapped("code")) if withholding_accounts else _("No accounts found")
        )
        
        return None, None, None, tooltip, raw_value

    def _prepare_cell_data_social_security_debt(self, company, speedy):
        """Calculate Social Security Debts"""
        # Search for social security debt accounts
        ss_accounts = self.env["account.account"].with_company(company).search([
            "|", "|",
            ("code", "ilike", "%segur%"),
            ("name", "ilike", "seguridad social"),
            ("name", "ilike", "social security"),
        ])
        
        if not ss_accounts:
            # Fallback: look for typical social security account patterns
            ss_accounts = self.env["account.account"].with_company(company).search([
                ("code", "=like", "2.1.3%"),  # Common SS debt range
            ])
        
        # Calculate balance directly for special handling
        domain = [
            ("company_id", "=", company.id),
            ("date", "<=", speedy["today"]),
            ("parent_state", "=", "posted"),
            ("account_id", "in", ss_accounts.ids)
        ]
        
        rg_res = self.env["account.move.line"]._read_group(
            domain, aggregates=["balance:sum"]
        )
        raw_value = abs(rg_res and rg_res[0][0] or 0)
        
        tooltip = _("Social security debts: %s") % (
            ", ".join(ss_accounts.mapped("code")) if ss_accounts else _("No accounts found")
        )
        
        return None, None, None, tooltip, raw_value

    def _prepare_cell_data_income_tax_provision(self, company, speedy):
        """Calculate Income Tax Provision"""
        # Search for income tax provision accounts
        tax_provision_accounts = self.env["account.account"].with_company(company).search([
            "|", "|",
            ("name", "ilike", "impuesto"),
            ("name", "ilike", "renta"),
            ("name", "ilike", "income tax"),
        ])
        
        if not tax_provision_accounts:
            # Fallback: look for typical tax provision patterns
            tax_provision_accounts = self.env["account.account"].with_company(company).search([
                ("code", "=like", "2.1.5%"),  # Common tax provision range
            ])
        
        # Calculate balance directly for special handling
        domain = [
            ("company_id", "=", company.id),
            ("date", "<=", speedy["today"]),
            ("parent_state", "=", "posted"),
            ("account_id", "in", tax_provision_accounts.ids)
        ]
        
        rg_res = self.env["account.move.line"]._read_group(
            domain, aggregates=["balance:sum"]
        )
        raw_value = abs(rg_res and rg_res[0][0] or 0)
        
        tooltip = _("Income tax provision: %s") % (
            ", ".join(tax_provision_accounts.mapped("code")) if tax_provision_accounts else _("No accounts found")
        )
        
        return None, None, None, tooltip, raw_value

    def _prepare_cell_data_pending_tax_refunds(self, company, speedy):
        """Calculate Pending Tax Refunds"""
        # Search for tax refund accounts (assets)
        refund_accounts = self.env["account.account"].with_company(company).search([
            "|", "|",
            ("name", "ilike", "devolucion"),
            ("name", "ilike", "tax refund"),
            ("name", "ilike", "reembolso"),
        ])
        
        if not refund_accounts:
            # Fallback: look for typical refund account patterns
            refund_accounts = self.env["account.account"].with_company(company).search([
                ("code", "=like", "1.1.5%"),  # Common refund receivable range
            ])
        
        # Calculate balance directly for special handling
        domain = [
            ("company_id", "=", company.id),
            ("date", "<=", speedy["today"]),
            ("parent_state", "=", "posted"),
            ("account_id", "in", refund_accounts.ids)
        ]
        
        rg_res = self.env["account.move.line"]._read_group(
            domain, aggregates=["balance:sum"]
        )
        raw_value = abs(rg_res and rg_res[0][0] or 0)
        
        tooltip = _("Pending tax refunds: %s") % (
            ", ".join(refund_accounts.mapped("code")) if refund_accounts else _("No accounts found")
        )
        
        return None, None, None, tooltip, raw_value

    def _prepare_cell_data_tax_credits_vs_debts_ratio(self, company, speedy):
        """Calculate Tax Credits vs Debts Ratio"""
        # Get VAT credits
        credit_accounts, _, _, _ = self._prepare_cell_data_vat_credit_balance(company, speedy)
        
        # Get VAT debts
        debt_accounts, _, _, _ = self._prepare_cell_data_vat_debt_balance(company, speedy)
        
        domain_base = [
            ("company_id", "=", company.id),
            ("date", "<=", speedy["today"]),
            ("parent_state", "=", "posted"),
        ]
        
        # Calculate credits
        credits = 0
        if credit_accounts:
            credit_domain = domain_base + [("account_id", "in", credit_accounts.ids)]
            credit_rg = self.env["account.move.line"]._read_group(
                credit_domain, aggregates=["balance:sum"]
            )
            credits = abs(credit_rg and credit_rg[0][0] or 0)
        
        # Calculate debts
        debts = 0
        if debt_accounts:
            debt_domain = domain_base + [("account_id", "in", debt_accounts.ids)]
            debt_rg = self.env["account.move.line"]._read_group(
                debt_domain, aggregates=["balance:sum"]
            )
            debts = abs(debt_rg and debt_rg[0][0] or 0)
        
        if debts > 0:
            ratio = credits / debts
            tooltip = _("Tax Credits: %s / Tax Debts: %s = %.2f") % (
                format_amount(self.env, credits, company.currency_id),
                format_amount(self.env, debts, company.currency_id),
                ratio
            )
            return None, None, None, tooltip, ratio
        
        return None, None, None, _("No tax debts to calculate ratio"), 0

    def _prepare_cell_data(self, company, speedy):
        """Inherit this method to change the computation of a cell type"""
        self.ensure_one()
        cell_type = self.cell_type
        value = raw_value = tooltip = warn = False
        
        # UNIVERSAL ACCOUNT SELECTION: Check if user has configured accounts
        # This allows any cell type to use custom account selection
        if hasattr(self, 'account_selection_mode') and self.account_selection_mode in ['specific', 'by_type']:
            accounts, tooltip = self._get_universal_accounts(company)
            if accounts:
                # Use the universal account balance method for any cell type
                accounts, sign, specific_domain, tooltip = self._prepare_cell_data_account_balance(company, speedy)
                if accounts:
                    domain = [
                        ("company_id", "=", company.id),
                        ("account_id", "in", accounts.ids),
                        ("date", "<=", speedy["today"]),
                        ("parent_state", "=", "posted"),
                    ]
                    rg_res = self.env["account.move.line"]._read_group(
                        domain, aggregates=["balance:sum"]
                    )
                    raw_value = sign * (rg_res and rg_res[0][0] or 0)
                    value = format_amount(self.env, raw_value, company.currency_id)
                    
                    # Usar el nuevo sistema de warning con colores
                    if self.warn:
                        warn_level = self._calculate_warning_level(raw_value)
                        warn = warn_level != 'safe'
                    else:
                        warn_level = 'safe'
                        warn = False
                    
                    # Calcular label con prioridad absoluta para custom_label
                    final_label = "KPI"  # Fallback por defecto
                    if self.custom_label and self.custom_label.strip():
                        final_label = self.custom_label.strip()
                    elif speedy.get("cell_type2label") and speedy["cell_type2label"].get(cell_type):
                        final_label = speedy["cell_type2label"][cell_type]
                    elif cell_type:
                        final_label = cell_type.replace('_', ' ').title()
                    
                    # Return dictionary format as expected by the system with all required fields
                    res = {
                        "cell_type": cell_type,
                        "label": final_label,
                        "value": value,
                        "raw_value": raw_value,
                        "warn": warn,
                        "warn_level": warn_level,
                        "color_info": {
                            "level": warn_level,
                            "use_colors": self.use_color_thresholds,
                            "description": self._get_warning_description(warn_level, raw_value)
                        },
                        "tooltip": self.custom_tooltip or tooltip,
                        "click_action": self.click_action,
                        "kpi_id": self.id,
                    }
                    
                    # Add target percentage if enabled
                    if self.show_target_percentage and self.target_value:
                        target_percentage = self._calculate_target_percentage(raw_value) if raw_value is not None else 0
                        res.update({
                            "show_target_percentage": True,
                            "target_value": self.target_value,
                            "target_percentage": target_percentage,
                            "target_percentage_formatted": f"{target_percentage:.1f}%" if target_percentage else "0.0%",
                            "target_value_formatted": format_amount(self.env, self.target_value, company.currency_id)
                        })
                    else:
                        res["show_target_percentage"] = False
                    
                    # Add warning configuration if enabled
                    if self.warn:
                        # Format warning values based on KPI type
                        warn_min_formatted = format_amount(self.env, self.warn_min, company.currency_id)
                        warn_max_formatted = format_amount(self.env, self.warn_max, company.currency_id)
                            
                        # Get human-readable warning type
                        warn_type_labels = dict(self.fields_get("warn_type", "selection")["warn_type"]["selection"])
                        
                        res.update({
                            "warn_config": {
                                "warn_min": self.warn_min,
                                "warn_max": self.warn_max,
                                "warn_min_formatted": warn_min_formatted,
                                "warn_max_formatted": warn_max_formatted,
                                "warn_type": self.warn_type,
                                "warn_type_label": warn_type_labels.get(self.warn_type, self.warn_type),
                            }
                        })
                    
                    # Add historical min/max if configured
                    if self.show_historical_range:
                        # Update historical values efficiently
                        self._update_historical_range(raw_value)
                        
                        res["historical_min"] = self.historical_min
                        res["historical_max"] = self.historical_max
                        res["show_historical_range"] = True
                        
                        # Format min/max for display
                        res["historical_min_formatted"] = format_amount(self.env, self.historical_min, company.currency_id)
                        res["historical_max_formatted"] = format_amount(self.env, self.historical_max, company.currency_id)
                    else:
                        res["show_historical_range"] = False
                    
                    return res
        
        if cell_type.endswith("lock_date"):
            raw_value = company[cell_type]
            value = raw_value and format_date(self.env, raw_value)
            tooltip = speedy["lock_date2help"][cell_type]
            if self.warn:
                if not raw_value:
                    warn = True
                elif raw_value < speedy["today"] - relativedelta(
                    days=self.warn_lock_date_days
                ):
                    warn = True
        else:
            accounts = False
            # Handle special cases first
            if cell_type in ['oldest_customer_invoice', 'oldest_supplier_invoice', 'receivable_payable_ratio', 'customer_invoices_count', 'supplier_bills_count', 'cost_income_ratio', 'kpi_math_operation', 'unreconciled_receivables_count', 'unreconciled_payables_count', 'unreconciled_bank_count', 'unreconciled_items_count', 'vat_credit_balance', 'vat_debt_balance', 'tax_withholdings_balance', 'social_security_debt', 'income_tax_provision', 'pending_tax_refunds', 'tax_credits_vs_debts_ratio']:
                specific_method = getattr(self, f"_prepare_cell_data_{cell_type}")
                accounts, sign, specific_domain, specific_tooltip, raw_value = specific_method(
                    company, speedy
                )
                if cell_type == 'receivable_payable_ratio':
                    value = f"{raw_value:.2f}" if raw_value else "0.00"
                elif cell_type in ['oldest_customer_invoice', 'oldest_supplier_invoice']:
                    value = f"{int(raw_value)} days" if raw_value else "0 days"
                elif cell_type in ['customer_invoices_count', 'supplier_bills_count', 'unreconciled_receivables_count', 'unreconciled_payables_count', 'unreconciled_bank_count', 'unreconciled_items_count']:
                    value = f"{int(raw_value)}" if raw_value else "0"
                elif cell_type in ['cost_income_ratio']:
                    value = f"{raw_value:.2f}%" if raw_value else "0.00%"
                elif cell_type == 'kpi_math_operation':
                    # Use custom formatting for mathematical operations
                    value = self._format_mathematical_result(raw_value, company) if raw_value is not None else "0"
                elif cell_type == 'tax_credits_vs_debts_ratio':
                    value = f"{raw_value:.2f}" if raw_value else "0.00"
                elif cell_type in ['vat_credit_balance', 'vat_debt_balance', 'tax_withholdings_balance', 'social_security_debt', 'income_tax_provision', 'pending_tax_refunds']:
                    value = format_amount(self.env, raw_value, company.currency_id) if raw_value else format_amount(self.env, 0, company.currency_id)
                tooltip = specific_tooltip
            elif hasattr(self, f"_prepare_cell_data_{cell_type}"):
                specific_method = getattr(self, f"_prepare_cell_data_{cell_type}")
                accounts, sign, specific_domain, specific_tooltip = specific_method(
                    company, speedy
                )
            elif cell_type.startswith("income_"):
                accounts, sign, specific_domain, specific_tooltip = (
                    self._prepare_cell_data_income(company, speedy)
                )
            if accounts:
                domain = (specific_domain or []) + [
                    ("company_id", "=", company.id),
                    ("account_id", "in", accounts.ids),
                    ("date", "<=", speedy["today"]),
                    ("parent_state", "=", "posted"),
                ]
                rg_res = self.env["account.move.line"]._read_group(
                    domain, aggregates=["balance:sum"]
                )
                assert sign in (1, -1)
                raw_value = rg_res and rg_res[0][0] * sign or 0
                value = format_amount(self.env, raw_value, company.currency_id)
                tooltip = _(
                    "Balance of account(s) %(account_codes)s%(specific)s.",
                    account_codes=", ".join(accounts.mapped("code")),
                    specific=specific_tooltip and f" {specific_tooltip}" or "",
                )
        # Calcular label con prioridad absoluta para custom_label
        final_label = "KPI"  # Fallback por defecto
        if self.custom_label and self.custom_label.strip():
            final_label = self.custom_label.strip()
        elif speedy.get("cell_type2label") and speedy["cell_type2label"].get(cell_type):
            final_label = speedy["cell_type2label"][cell_type]
        elif cell_type:
            final_label = cell_type.replace('_', ' ').title()
        
        res = {
            "cell_type": cell_type,
            "label": final_label,
            "raw_value": raw_value,
            "value": value or _("None"),
            "tooltip": self.custom_tooltip or tooltip,
            "warn": warn,
            "click_action": self.click_action,
            "kpi_id": self.id,
        }
        
        # Add target percentage if enabled
        if self.show_target_percentage and self.target_value:
            target_percentage = self._calculate_target_percentage(raw_value) if raw_value is not None else 0
            res.update({
                "show_target_percentage": True,
                "target_value": self.target_value,
                "target_percentage": target_percentage,
                "target_percentage_formatted": f"{target_percentage:.1f}%" if target_percentage else "0.0%",
                "target_value_formatted": format_amount(self.env, self.target_value, company.currency_id)
            })
        else:
            res["show_target_percentage"] = False
        
        # Add warning configuration if enabled
        if self.warn:
            # Format warning values based on KPI type
            if self.cell_type == 'kpi_math_operation':
                warn_min_formatted = self._format_mathematical_result(self.warn_min, company)
                warn_max_formatted = self._format_mathematical_result(self.warn_max, company)
            else:
                warn_min_formatted = format_amount(self.env, self.warn_min, company.currency_id)
                warn_max_formatted = format_amount(self.env, self.warn_max, company.currency_id)
                
            # Get human-readable warning type
            warn_type_labels = dict(self.fields_get("warn_type", "selection")["warn_type"]["selection"])
            
            res.update({
                "warn_config": {
                    "warn_min": self.warn_min,
                    "warn_max": self.warn_max,
                    "warn_min_formatted": warn_min_formatted,
                    "warn_max_formatted": warn_max_formatted,
                    "warn_type": self.warn_type,
                    "warn_type_label": warn_type_labels.get(self.warn_type, self.warn_type),
                }
            })
        
        # Add historical min/max if configured
        if self.show_historical_range:
            # Update historical values efficiently
            self._update_historical_range(raw_value)
            
            res["historical_min"] = self.historical_min
            res["historical_max"] = self.historical_max
            res["show_historical_range"] = True
            
            # Format min/max for display
            if self.cell_type == 'kpi_math_operation':
                res["historical_min_formatted"] = self._format_mathematical_result(self.historical_min, company)
                res["historical_max_formatted"] = self._format_mathematical_result(self.historical_max, company)
            else:
                res["historical_min_formatted"] = format_amount(self.env, self.historical_min, company.currency_id)
                res["historical_max_formatted"] = format_amount(self.env, self.historical_max, company.currency_id)
        else:
            res["show_historical_range"] = False
        
        return res

    def action_view_records(self):
        """Acción para ver registros relacionados al hacer click en KPI"""
        self.ensure_one()
        
        if self.click_action == 'none':
            return {'type': 'ir.actions.client', 'tag': 'display_notification',
                   'params': {'title': _('No Action'), 'message': _('No action configured for this KPI'),
                             'type': 'info', 'sticky': False}}
        
        # Configurar acción según el tipo
        action = self._get_click_action_config()
        
        if not action:
            return {'type': 'ir.actions.client', 'tag': 'display_notification',
                   'params': {'title': _('Error'), 'message': _('Could not determine action for this KPI'),
                             'type': 'warning', 'sticky': False}}
        
        # Aplicar dominio personalizado si existe
        if self.action_domain:
            try:
                custom_domain = eval(self.action_domain)
                if action.get('domain'):
                    action['domain'] = expression.AND([action['domain'], custom_domain])
                else:
                    action['domain'] = custom_domain
            except Exception as e:
                return {'type': 'ir.actions.client', 'tag': 'display_notification',
                       'params': {'title': _('Domain Error'), 'message': str(e),
                                 'type': 'danger', 'sticky': True}}
        
        return action

    @api.model  
    def action_view_records_static(self, kpi_type, click_action, action_domain):
        """Static method for viewing records from JavaScript"""
        try:
            # Find KPI by type
            kpi = self.search([('cell_type', '=', kpi_type)], limit=1)
            if not kpi:
                return {'type': 'ir.actions.client', 'tag': 'display_notification',
                       'params': {'title': _('Error'), 'message': _('KPI not found'),
                                 'type': 'danger', 'sticky': False}}
            
            # Use provided parameters or fall back to configured ones
            click_action = click_action or kpi.click_action
            action_domain = action_domain or kpi.action_domain
            
            if click_action == 'none':
                return {'type': 'ir.actions.client', 'tag': 'display_notification',
                       'params': {'title': _('No Action'), 'message': _('No action configured for this KPI'),
                                 'type': 'info', 'sticky': False}}
            
            # Get action configuration
            action = kpi._get_click_action_config()
            
            if not action:
                return {'type': 'ir.actions.client', 'tag': 'display_notification',
                       'params': {'title': _('Error'), 'message': _('Could not determine action for this KPI'),
                                 'type': 'warning', 'sticky': False}}
            
            # Apply custom domain if provided
            if action_domain:
                try:
                    custom_domain = eval(action_domain) if isinstance(action_domain, str) else action_domain
                    if action.get('domain'):
                        action['domain'] = expression.AND([action['domain'], custom_domain])
                    else:
                        action['domain'] = custom_domain
                except Exception as e:
                    return {'type': 'ir.actions.client', 'tag': 'display_notification',
                           'params': {'title': _('Domain Error'), 'message': str(e),
                                     'type': 'danger', 'sticky': True}}
            
            return action
            
        except Exception as e:
            return {'type': 'ir.actions.client', 'tag': 'display_notification',
                   'params': {'title': _('Navigation Error'), 'message': str(e),
                             'type': 'danger', 'sticky': True}}

    def _get_click_action_config(self):
        """Configurar la acción según el tipo de KPI"""
        company = self.env.company
        
        # Casos especiales que necesitan modelos diferentes
        if self.cell_type in ['customer_invoices_count', 'supplier_bills_count']:
            if self.cell_type == 'customer_invoices_count':
                return {
                    'name': _('Customer Invoices'),
                    'res_model': 'account.move',
                    'view_mode': 'list,form',
                    'type': 'ir.actions.act_window',
                    'domain': [
                        ('move_type', '=', 'out_invoice'),
                        ('state', 'in', ['draft', 'posted']),
                        ('company_id', '=', company.id)
                    ],
                    'context': {'create': False},
                }
            elif self.cell_type == 'supplier_bills_count':
                return {
                    'name': _('Vendor Bills'),
                    'res_model': 'account.move',
                    'view_mode': 'list,form', 
                    'type': 'ir.actions.act_window',
                    'domain': [
                        ('move_type', '=', 'in_invoice'),
                        ('state', 'in', ['draft', 'posted']),
                        ('company_id', '=', company.id)
                    ],
                    'context': {'create': False},
                }
        
        action_configs = {
            'account_move': {
                'name': _('Journal Entries'),
                'res_model': 'account.move.line',  # Usar account.move.line para mejores filtros
                'view_mode': 'list,form',
                'type': 'ir.actions.act_window',
                'context': {'create': False},  # No permitir crear desde esta vista
            },
            'account_account': {
                'name': _('Chart of Accounts'),
                'res_model': 'account.account',
                'view_mode': 'list,form',
                'type': 'ir.actions.act_window',
            },
            'res_partner': {
                'name': _('Partners'),
                'res_model': 'res.partner',
                'view_mode': 'kanban,list,form',
                'type': 'ir.actions.act_window',
            },
            'account_payment': {
                'name': _('Payments'),
                'res_model': 'account.payment',
                'view_mode': 'list,form',
                'type': 'ir.actions.act_window',
            }
        }
        
        action = action_configs.get(self.click_action)
        if not action:
            return None
            
        # Usar dominio personalizado si está configurado, sino usar dominio por defecto
        if self.action_domain:
            try:
                # Evaluar el dominio personalizado de forma segura
                import ast
                custom_domain = ast.literal_eval(self.action_domain)
                if isinstance(custom_domain, list):
                    action['domain'] = custom_domain
                else:
                    # Si no es una lista válida, usar dominio por defecto
                    domain = self._get_default_domain_for_kpi()
                    if domain:
                        action['domain'] = domain
            except (ValueError, SyntaxError):
                # Si hay error en el dominio personalizado, usar dominio por defecto
                domain = self._get_default_domain_for_kpi()
                if domain:
                    action['domain'] = domain
        else:
            # No hay dominio personalizado, usar dominio por defecto
            domain = self._get_default_domain_for_kpi()
            if domain:
                action['domain'] = domain
            
        return action

    def _get_default_domain_for_kpi(self):
        """Obtener dominio por defecto según el tipo de KPI"""
        company = self.env.company
        
        # Para Journal Entries (account.move.line) usamos dominios más específicos
        if self.click_action == 'account_move':
            domain_configs = {
                'customer_debt': [
                    ('account_id.account_type', '=', 'asset_receivable'), 
                    ('company_id', '=', company.id),
                    ('parent_state', '=', 'posted')
                ],
                'supplier_debt': [
                    ('account_id.account_type', '=', 'liability_payable'), 
                    ('company_id', '=', company.id),
                    ('parent_state', '=', 'posted')
                ],
                'liquidity': [
                    ('account_id.account_type', '=', 'asset_cash'), 
                    ('company_id', '=', company.id),
                    ('parent_state', '=', 'posted')
                ],
                'unreconciled_receivables_count': [
                    ('account_id.account_type', '=', 'asset_receivable'), 
                    ('company_id', '=', company.id),
                    ('parent_state', '=', 'posted'),
                    ('reconciled', '=', False)
                ],
                'unreconciled_payables_count': [
                    ('account_id.account_type', '=', 'liability_payable'), 
                    ('company_id', '=', company.id),
                    ('parent_state', '=', 'posted'),
                    ('reconciled', '=', False)
                ],
                'unreconciled_bank_count': [
                    ('account_id.account_type', '=', 'asset_cash'), 
                    ('company_id', '=', company.id),
                    ('parent_state', '=', 'posted'),
                    ('reconciled', '=', False)
                ],
                'unreconciled_items_count': [
                    ('company_id', '=', company.id),
                    ('parent_state', '=', 'posted'),
                    ('reconciled', '=', False)
                ],
            }
            # Para Account Balance, usar el tipo de cuenta configurado
            if self.cell_type == 'account_balance' and self.account_selection_mode == 'by_type':
                if hasattr(self, 'account_type') and self.account_type:
                    return [
                        ('account_id.account_type', '=', self.account_type),
                        ('company_id', '=', company.id),
                        ('parent_state', '=', 'posted')
                    ]
            
            return domain_configs.get(self.cell_type, [
                ('company_id', '=', company.id),
                ('parent_state', '=', 'posted')
            ])
        
        # Para otros tipos de modelos
        elif self.click_action == 'account_account':
            domain_configs = {
                'customer_debt': [('account_type', '=', 'asset_receivable'), ('company_id', '=', company.id)],
                'supplier_debt': [('account_type', '=', 'liability_payable'), ('company_id', '=', company.id)],
                'liquidity': [('account_type', '=', 'asset_cash'), ('company_id', '=', company.id)],
                'unreconciled_receivables_count': [('account_type', '=', 'asset_receivable'), ('company_id', '=', company.id)],
                'unreconciled_payables_count': [('account_type', '=', 'liability_payable'), ('company_id', '=', company.id)],
                'unreconciled_bank_count': [('account_type', '=', 'asset_cash'), ('company_id', '=', company.id)],
                'unreconciled_items_count': [('company_id', '=', company.id)],
            }
            return domain_configs.get(self.cell_type, [('company_id', '=', company.id)])
        
        # Dominio general
        return [('company_id', '=', company.id)]

    def _update_cell_warn(self, cell_data):
        self.ensure_one()
        if (
            self.warn
            and self.warn_type
            and isinstance(cell_data["raw_value"], (int | float))
        ):
            raw_value = cell_data["raw_value"]
            warn_level = self._calculate_warning_level(raw_value)
            
            # Actualizar cell_data con información de color
            cell_data["warn"] = warn_level != 'safe'
            cell_data["warn_level"] = warn_level  # 'danger', 'warning', 'safe'
            
            # Información adicional para el frontend
            cell_data["color_info"] = {
                "level": warn_level,
                "use_colors": self.use_color_thresholds,
                "description": self._get_warning_description(warn_level, raw_value)
            }
    
    def _calculate_warning_level(self, raw_value):
        """Calculate warning level: 'danger', 'warning', or 'safe'"""
        if not self.warn or not self.warn_type:
            return 'safe'
            
        # Check if value is in danger zone (red)
        is_danger = False
        if (
            (self.warn_type == "under" and raw_value < self.warn_min)
            or (self.warn_type == "above" and raw_value > self.warn_max)
            or (
                self.warn_type == "outside"
                and (raw_value < self.warn_min or raw_value > self.warn_max)
            )
            or (
                self.warn_type == "inside"
                and raw_value > self.warn_min
                and raw_value < self.warn_max
            )
        ):
            is_danger = True
            
        if is_danger:
            return 'danger'  # Red
            
        # Check if using color thresholds for yellow zone
        if not self.use_color_thresholds:
            return 'safe'  # Green/normal
            
        # Calculate if in warning zone (yellow) - close to limits
        is_warning = self._is_in_warning_zone(raw_value)
        
        return 'warning' if is_warning else 'safe'  # Yellow or Green
    
    def _is_in_warning_zone(self, raw_value):
        """Check if value is in warning zone (close to limits)"""
        if not self.use_color_thresholds:
            return False
            
        threshold_pct = self.yellow_threshold_percentage / 100.0
        
        if self.warn_type == "under":
            # Close to minimum threshold
            buffer = abs(self.warn_min) * threshold_pct
            return self.warn_min <= raw_value < (self.warn_min + buffer)
            
        elif self.warn_type == "above":
            # Close to maximum threshold  
            buffer = abs(self.warn_max) * threshold_pct
            return (self.warn_max - buffer) < raw_value <= self.warn_max
            
        elif self.warn_type == "outside":
            # Close to either min or max
            min_buffer = abs(self.warn_min) * threshold_pct
            max_buffer = abs(self.warn_max) * threshold_pct
            
            near_min = self.warn_min <= raw_value < (self.warn_min + min_buffer)
            near_max = (self.warn_max - max_buffer) < raw_value <= self.warn_max
            
            return near_min or near_max
            
        elif self.warn_type == "inside":
            # Close to boundaries of the inside range
            range_size = self.warn_max - self.warn_min
            buffer = range_size * threshold_pct
            
            near_min_boundary = (self.warn_min - buffer) <= raw_value < self.warn_min
            near_max_boundary = self.warn_max < raw_value <= (self.warn_max + buffer)
            
            return near_min_boundary or near_max_boundary
            
        return False
    
    def _get_warning_description(self, warn_level, raw_value):
        """Get human-readable description of warning level"""
        if warn_level == 'danger':
            return f"Value {raw_value} is outside safe limits"
        elif warn_level == 'warning':
            return f"Value {raw_value} is approaching limits"
        else:
            return f"Value {raw_value} is within safe range"
    
    def _calculate_target_percentage(self, raw_value):
        """Calculate achievement percentage against target value"""
        if not self.target_value or not self.show_target_percentage:
            return None
            
        if self.target_value == 0:
            return 0
            
        # For ratio KPIs, percentage calculation might need different logic
        if self.cell_type in ['receivable_payable_ratio', 'cost_income_ratio', 'gross_margin_sales_ratio', 
                              'operating_expenses_sales_ratio', 'costs_sales_ratio']:
            # For ratios, calculate how close we are to target (100% = exact match)
            if self.target_value == raw_value:
                return 100.0
            else:
                # Calculate relative percentage - closer to target = higher percentage
                difference_percentage = abs((raw_value - self.target_value) / self.target_value) * 100
                return max(0, 100 - difference_percentage)
        else:
            # For absolute values (amounts, counts), calculate direct percentage
            percentage = (raw_value / self.target_value) * 100
            return max(0, percentage)  # Don't allow negative percentages

    @api.depends("cell_type", "custom_label")
    def _get_account_type_description(self, account_types):
        """Convert account types to human readable descriptions"""
        type_descriptions = {
            # Asset Types
            'asset_receivable': 'Cuentas por Cobrar',
            'asset_cash': 'Efectivo y Bancos',
            'asset_current': 'Activos Circulantes',
            'asset_non_current': 'Activos No Circulantes',
            'asset_prepayments': 'Pagos Anticipados',
            'asset_fixed': 'Activos Fijos',
            
            # Liability Types
            'liability_payable': 'Cuentas por Pagar',
            'liability_credit_card': 'Tarjetas de Crédito',
            'liability_current': 'Pasivos Circulantes',
            'liability_non_current': 'Pasivos No Circulantes',
            
            # Income Types
            'income': 'Ingresos',
            'income_other': 'Otros Ingresos',
            
            # Expense Types
            'expense': 'Gastos Operativos',
            'expense_direct_cost': 'Costos Directos (COGS)',
            'expense_depreciation': 'Depreciación',
        }
        
        if isinstance(account_types, str):
            account_types = [account_types]
            
        descriptions = []
        for account_type in account_types:
            if account_type in type_descriptions:
                descriptions.append(type_descriptions[account_type])
            else:
                descriptions.append(account_type.replace('_', ' ').title())
                
        if len(descriptions) == 1:
            return descriptions[0]
        elif len(descriptions) <= 3:
            return ' + '.join(descriptions)
        else:
            return f"{descriptions[0]} + {len(descriptions)-1} más"

    def _get_enhanced_display_name(self):
        """Generate enhanced display names based on account types or specific accounts used"""
        type2name = dict(
            self.fields_get("cell_type", "selection")["cell_type"]["selection"]
        )
        
        base_name = type2name.get(self.cell_type, self.cell_type or "")
        
        # For liquidity KPIs with specific accounts
        if self.cell_type == 'liquidity' and self.liquidity_mode == 'specific_accounts' and self.specific_account_ids:
            if len(self.specific_account_ids) == 1:
                account = self.specific_account_ids[0]
                return f"{base_name} - {account.name} ({account.code})"
            else:
                account_names = [f"{acc.name} ({acc.code})" for acc in self.specific_account_ids[:2]]
                if len(self.specific_account_ids) > 2:
                    account_names.append(f"+ {len(self.specific_account_ids)-2} más")
                return f"{base_name} - {', '.join(account_names)}"
        
        # For KPIs that use specific account types, add type description
        account_type_mapping = {
            # Asset-based KPIs
            'total_assets': ['asset_receivable', 'asset_cash', 'asset_current', 'asset_non_current'],
            
            # Liability-based KPIs  
            'total_liabilities': ['liability_payable', 'liability_credit_card', 'liability_current', 'liability_non_current'],
            
            # Income-based KPIs
            'income_fiscalyear': ['income', 'income_other'],
            'income_year': ['income', 'income_other'],
            'income_quarter': ['income', 'income_other'],
            'income_month': ['income', 'income_other'],
            'ebit': ['income', 'income_other'],
            'ebit_ratio': ['income', 'income_other'],
            'gross_income': ['income', 'income_other'],
            'ebit_assets_ratio': ['income', 'income_other'],
            'nopat': ['income', 'income_other'],
            'nopat_assets_ratio': ['income', 'income_other'],
            'profit_sales_ratio': ['income', 'income_other'],
            'gross_margin_sales_ratio': ['income', 'income_other'],
            'cost_income_ratio': ['income', 'income_other'],
            
            # Mixed KPIs
            'operating_expenses_sales_ratio': ['expense'],  # Expenses
            'costs_sales_ratio': ['expense_direct_cost'],   # Direct costs
            'receivable_payable_ratio': ['asset_receivable', 'liability_payable'],  # Both
            
            # Tax & Fiscal KPIs
            'vat_credit_balance': 'VAT Credits',
            'vat_debt_balance': 'VAT Debts',
            'tax_withholdings_balance': 'Tax Withholdings',
            'social_security_debt': 'Social Security Debts',
            'income_tax_provision': 'Income Tax Provision',
            'pending_tax_refunds': 'Pending Tax Refunds',
            'tax_credits_vs_debts_ratio': 'Tax Credits vs Debts Ratio',
        }
        
        if self.cell_type in account_type_mapping:
            account_types = account_type_mapping[self.cell_type]
            
            # Handle fiscal KPIs with text descriptions
            if isinstance(account_types, str):
                type_desc = account_types
            else:
                type_desc = self._get_account_type_description(account_types)
            
            # Special formatting for ratio KPIs
            if 'ratio' in self.cell_type.lower():
                return f"{base_name} ({type_desc})"
            else:
                return f"{base_name} - {type_desc}"
        
        # For customer/supplier debt (uses receivable/payable account types)
        if self.cell_type in ['customer_debt', 'customer_overdue']:
            return f"{base_name} - {self._get_account_type_description('asset_receivable')}"
        elif self.cell_type == 'supplier_debt':
            return f"{base_name} - {self._get_account_type_description('liability_payable')}"
            
        # For liquidity with all accounts
        elif self.cell_type == 'liquidity' and self.liquidity_mode == 'all_accounts':
            return f"{base_name} - {self._get_account_type_description(['asset_cash', 'asset_current'])}"
        
        # Default case
        return base_name

    def _compute_display_name(self):
        for cell in self:
            display_name = "-"
            if cell.custom_label:
                display_name = cell.custom_label
            elif cell.cell_type:
                display_name = cell._get_enhanced_display_name()
                    
            cell.display_name = display_name

    def _prepare_cell_data_receivable_payable_ratio(self, company, speedy):
        """Calculate Receivable / Payable Ratio"""
        # Get receivable accounts
        receivable_accounts = (
            self.env["res.partner"]
            ._fields["property_account_receivable_id"]
            .get_company_dependent_fallback(self.env["res.partner"])
        )
        
        # Get payable accounts
        payable_accounts = (
            self.env["res.partner"]
            ._fields["property_account_payable_id"]
            .get_company_dependent_fallback(self.env["res.partner"])
        )
        
        domain_base = [
            ("company_id", "=", company.id),
            ("date", "<=", speedy["today"]),
            ("parent_state", "=", "posted"),
        ]
        
        # Calculate receivables
        receivable_domain = domain_base + [("account_id", "in", receivable_accounts.ids)]
        receivable_rg = self.env["account.move.line"]._read_group(
            receivable_domain, aggregates=["balance:sum"]
        )
        receivables = abs(receivable_rg and receivable_rg[0][0] or 0)
        
        # Calculate payables
        payable_domain = domain_base + [("account_id", "in", payable_accounts.ids)]
        payable_rg = self.env["account.move.line"]._read_group(
            payable_domain, aggregates=["balance:sum"]
        )
        payables = abs(payable_rg and payable_rg[0][0] or 0)
        
        if payables > 0:
            ratio = receivables / payables
        else:
            ratio = 0
        
        tooltip = f"Receivables: {format_amount(self.env, receivables, company.currency_id)}\n" \
                  f"Payables: {format_amount(self.env, payables, company.currency_id)}"
        
        return None, None, None, tooltip, ratio
