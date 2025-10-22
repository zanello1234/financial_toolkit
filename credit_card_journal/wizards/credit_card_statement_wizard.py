# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CreditCardStatementWizard(models.TransientModel):
    _name = 'credit.card.statement.wizard'
    _description = 'Credit Card Statement Generation Wizard'

    journal_id = fields.Many2one('account.journal', string='Credit Card Journal', required=True, readonly=True)
    closing_date = fields.Date(string='Fecha de Cierre', required=True, default=fields.Date.today)
    due_date = fields.Date(string='Fecha de Vencimiento', required=True)
    
    # Statement charges/fees
    taxes_amount = fields.Monetary(string='Impuestos', currency_field='currency_id', default=0.0)
    interest_amount = fields.Monetary(string='Intereses', currency_field='currency_id', default=0.0)
    stamp_amount = fields.Monetary(string='Sellados', currency_field='currency_id', default=0.0)
    other_charges_amount = fields.Monetary(string='Otros Gastos', currency_field='currency_id', default=0.0)
    
    currency_id = fields.Many2one('res.currency', related='journal_id.currency_id', readonly=True)
    
    # Wizard state management
    state = fields.Selection([
        ('import', 'Importar Transacciones'),
        ('charges', 'Agregar Gastos'),  
        ('close', 'Cerrar Resumen')
    ], string='Estado', default='import')
    
    # Associated statement
    statement_id = fields.Many2one(
        'account.bank.statement',
        string='Statement Asociado',
        help="Statement created by this wizard"
    )
    
    # Cached consumption values (stored after generation)
    cached_consumptions_ars = fields.Monetary(
        string='Consumos ARS (Calculados)',
        currency_field='currency_id',
        help="Cached ARS consumptions after statement generation"
    )
    cached_consumptions_usd = fields.Monetary(
        string='Consumos USD (Calculados)', 
        currency_field='currency_id',
        help="Cached USD consumptions after statement generation"
    )
    cached_consumptions_total = fields.Monetary(
        string='Total Consumos (Calculados)',
        currency_field='currency_id',
        help="Cached total consumptions after statement generation"
    )
    
    # Credit card payments during the period
    payments_ars = fields.Monetary(
        string='Pagos en Pesos (ARS)',
        currency_field='currency_id',
        compute='_compute_payments_by_currency',
        readonly=True
    )
    payments_usd = fields.Monetary(
        string='Pagos en Dólares (USD)',
        currency_field='currency_id',
        compute='_compute_payments_by_currency',
        readonly=True
    )
    payments_total = fields.Monetary(
        string='Total Pagos',
        currency_field='currency_id',
        compute='_compute_payments_total',
        readonly=True
    )
    
    # Calculated fields
    previous_balance = fields.Monetary(
        string='Saldo Anterior', 
        currency_field='currency_id', 
        compute='_compute_previous_balance',
        readonly=True
    )
    total_charges = fields.Monetary(
        string='Total Gastos del Resumen', 
        currency_field='currency_id', 
        compute='_compute_total_charges',
        readonly=True
    )
    consumptions_total = fields.Monetary(
        string='Total Consumos', 
        currency_field='currency_id', 
        compute='_compute_consumptions_total',
        readonly=True
    )
    consumptions_ars = fields.Monetary(
        string='Consumos en Pesos (ARS)', 
        currency_field='currency_id', 
        compute='_compute_consumptions_by_currency',
        readonly=True
    )
    consumptions_usd = fields.Monetary(
        string='Consumos en Dólares (USD)', 
        currency_field='currency_id', 
        compute='_compute_consumptions_by_currency',
        readonly=True
    )
    total_to_pay = fields.Monetary(
        string='Total a Pagar', 
        currency_field='currency_id', 
        compute='_compute_total_to_pay',
        readonly=True
    )
    total_to_pay_ars = fields.Monetary(
        string='Total a Pagar (ARS)', 
        currency_field='currency_id', 
        compute='_compute_total_to_pay_by_currency',
        readonly=True
    )
    total_to_pay_usd = fields.Monetary(
        string='Total a Pagar (USD)', 
        currency_field='currency_id', 
        compute='_compute_total_to_pay_by_currency',
        readonly=True
    )
    last_closing_date = fields.Date(
        string='Último Cierre', 
        compute='_compute_last_statement_info',
        readonly=True
    )
    last_due_date = fields.Date(
        string='Último Vencimiento', 
        compute='_compute_last_statement_info',
        readonly=True
    )

    
    @api.depends('taxes_amount', 'interest_amount', 'stamp_amount', 'other_charges_amount')
    def _compute_total_charges(self):
        """Calculate total charges/fees for the statement"""
        for record in self:
            record.total_charges = (
                record.taxes_amount + record.interest_amount + 
                record.stamp_amount + record.other_charges_amount
            )
    
    @api.depends('journal_id', 'closing_date', 'state', 'cached_consumptions_total')
    def _compute_consumptions_total(self):
        """Calculate total consumptions (payments) for the period"""
        for record in self:
            # Use cached value if available (after statement generation)
            if record.cached_consumptions_total > 0:
                record.consumptions_total = record.cached_consumptions_total
                continue
                
            if not record.journal_id or not record.closing_date:
                record.consumptions_total = 0.0
                continue
                
            # Calculate date range (from first day of month to closing date)
            start_date = record.closing_date.replace(day=1)
            end_date = record.closing_date
            
            # Get payments not already included in other statements
            payments = record._get_available_payments(start_date, end_date)
            
            # Sum all payments (should be negative for expenses)
            total = sum(payment.amount for payment in payments)
            record.consumptions_total = abs(total)  # Show as positive for UI
    
    @api.depends('total_charges', 'consumptions_ars', 'consumptions_usd', 'closing_date', 'state')
    def _compute_total_to_pay(self):
        """Calculate total amount to pay (ARS + USD converted to ARS using closing date exchange rate)"""
        for record in self:
            if not record.closing_date:
                record.total_to_pay = record.consumptions_total + record.total_charges
                continue
                
            # Get ARS and USD currencies
            ars_currency = self.env['res.currency'].search([('name', '=', 'ARS')], limit=1)
            usd_currency = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
            
            if not ars_currency or not usd_currency:
                # Fallback to simple sum if currencies not found
                record.total_to_pay = record.consumptions_total + record.total_charges
                continue
            
            # Convert USD total to ARS using closing date exchange rate
            usd_in_ars = usd_currency._convert(
                record.total_to_pay_usd,
                ars_currency,
                record.journal_id.company_id,
                record.closing_date
            )
            
            # Total general = ARS total + USD total converted to ARS
            record.total_to_pay = record.total_to_pay_ars + usd_in_ars
    
    @api.depends('consumptions_ars', 'consumptions_usd', 'total_charges', 'payments_ars', 'payments_usd', 'state')
    def _compute_total_to_pay_by_currency(self):
        """Calculate total amount to pay separated by currency (ARS and USD)
        Formula: Saldo Anterior + Gastos + Consumos - Pagos
        Convention: Negative = Debt (a pagar), Positive = Credit balance (a favor)
        
        IMPORTANT: All values here are stored as POSITIVE amounts for UI display,
        but the calculation treats them as debt (negative) conceptually"""
        for record in self:
            # ARS total calculation:
            # Previous balance (negative if debt) + consumptions (debt) + charges (debt) - payments (reduces debt)
            # Note: All displayed values are positive, but we treat consumptions and charges as additions to debt
            ars_debt = abs(record.previous_balance) if record.previous_balance < 0 else -record.previous_balance
            ars_debt += record.consumptions_ars  # Add consumptions to debt
            ars_debt += record.total_charges     # Add charges to debt  
            ars_debt -= record.payments_ars      # Subtract payments from debt
            
            # Store as negative if it's debt, positive if credit balance
            record.total_to_pay_ars = -ars_debt if ars_debt > 0 else abs(ars_debt)
            
            # USD total calculation (simpler, no previous balance in USD typically)
            usd_debt = record.consumptions_usd - record.payments_usd
            record.total_to_pay_usd = -usd_debt if usd_debt > 0 else abs(usd_debt)
            
            _logger.info(f"Total calculation - Previous: {record.previous_balance}, Consumptions ARS: {record.consumptions_ars}, Charges: {record.total_charges}, Payments ARS: {record.payments_ars}")
            _logger.info(f"Result - Total ARS: {record.total_to_pay_ars}, Total USD: {record.total_to_pay_usd}")
    
    @api.depends('journal_id', 'closing_date', 'state', 'cached_consumptions_ars', 'cached_consumptions_usd')
    def _compute_consumptions_by_currency(self):
        """Calculate consumptions (payments made with credit card) separated by currency (ARS and USD)
        Only includes payments with state 'in_process'"""
        for record in self:
            # Use cached values if available (after statement generation) and state is 'close'
            if record.state == 'close' and (record.cached_consumptions_ars != 0 or record.cached_consumptions_usd != 0):
                record.consumptions_ars = record.cached_consumptions_ars
                record.consumptions_usd = record.cached_consumptions_usd
                _logger.info(f"Using cached consumptions - ARS: {record.cached_consumptions_ars}, USD: {record.cached_consumptions_usd}")
                continue
                
            if not record.journal_id or not record.closing_date:
                record.consumptions_ars = 0.0
                record.consumptions_usd = 0.0
                continue
                
            # Calculate date range: from last statement closing date + 1 day to current closing date
            last_statement = self.env['account.bank.statement'].search([
                ('journal_id', '=', record.journal_id.id),
                ('is_credit_card_statement', '=', True),
                ('date', '<', record.closing_date),
            ], order='date desc', limit=1)
            
            if last_statement and last_statement.closing_date:
                start_date = last_statement.closing_date + timedelta(days=1)
            else:
                # If no previous statement, use first day of month
                start_date = record.closing_date.replace(day=1)
            
            end_date = record.closing_date
            
            _logger.info(f"Looking for consumption payments (in_process) between {start_date} and {end_date}")
            
            # Get payments FROM this credit card journal (consumptions/purchases)
            # FIXED: Add supplier filter to ensure we only get supplier payments
            consumption_payments = self.env['account.payment'].search([
                ('journal_id', '=', record.journal_id.id),  # Payments FROM this credit card
                ('state', '=', 'in_process'),  # Only in_process payments
                ('date', '>=', start_date),
                ('date', '<=', end_date),
                ('payment_type', '=', 'outbound'),  # Outbound payments (purchases)
                ('partner_id.supplier_rank', '>', 0),  # Only supplier payments (purchases)
            ])
            
            _logger.info(f"Found {len(consumption_payments)} consumption payments (in_process) to suppliers in period")
            
            # Get payments already included in statements to avoid duplicates
            existing_statement_lines = self.env['account.bank.statement.line'].search([
                ('statement_id.journal_id', '=', record.journal_id.id),
                ('payment_ref', 'in', consumption_payments.mapped('name')),  # More precise filtering
            ])
            
            # Get payment names already used in statement lines
            used_payment_names = set(existing_statement_lines.mapped('payment_ref'))
            
            # Filter out payments already included in statements
            available_consumptions = consumption_payments.filtered(
                lambda p: p.name not in used_payment_names
            )
            
            _logger.info(f"Available consumption payments after filtering: {len(available_consumptions)}")
            
            # Separate consumptions by currency
            ars_total = 0.0
            usd_total = 0.0
            
            for payment in available_consumptions:
                _logger.info(f"Processing consumption payment: {payment.name}, Amount: {payment.amount}, Currency: {payment.currency_id.name if payment.currency_id else 'Company Currency'}")
                
                if payment.currency_id and payment.currency_id.name == 'USD':
                    usd_total += payment.amount
                elif payment.currency_id and payment.currency_id.name == 'ARS':
                    ars_total += payment.amount
                else:
                    # Default to company currency (usually ARS)
                    company_currency = record.journal_id.company_id.currency_id
                    if company_currency.name == 'USD':
                        usd_total += payment.amount
                    else:
                        ars_total += payment.amount
            
            record.consumptions_ars = ars_total
            record.consumptions_usd = usd_total
            
            _logger.info(f"Final consumption payments - ARS: {ars_total}, USD: {usd_total}")
    
    @api.depends('journal_id', 'closing_date', 'state')
    def _compute_payments_by_currency(self):
        """Calculate payments TO credit card separated by currency (ARS and USD)
        Only includes payments with state 'in_process'"""
        for record in self:
            if not record.journal_id or not record.closing_date:
                record.payments_ars = 0.0
                record.payments_usd = 0.0
                continue
                
            # Calculate date range: from last statement closing date + 1 day to current closing date
            last_statement = self.env['account.bank.statement'].search([
                ('journal_id', '=', record.journal_id.id),
                ('is_credit_card_statement', '=', True),
                ('date', '<', record.closing_date),
            ], order='date desc', limit=1)
            
            if last_statement and last_statement.closing_date:
                start_date = last_statement.closing_date + timedelta(days=1)
            else:
                # If no previous statement, use first day of month
                start_date = record.closing_date.replace(day=1)
            
            end_date = record.closing_date
            
            _logger.info(f"Looking for credit card payments (in_process) between {start_date} and {end_date}")
            
            # Get payments TO this credit card journal (payments to reduce debt)
            credit_card_payments = self.env['account.payment'].search([
                ('destination_journal_id', '=', record.journal_id.id),  # Payments TO this credit card
                ('state', '=', 'in_process'),  # Only in_process payments
                ('date', '>=', start_date),
                ('date', '<=', end_date),
                ('payment_type', '=', 'outbound'),  # Outbound from source (to pay credit card)
            ])
            
            _logger.info(f"Found {len(credit_card_payments)} credit card payments (in_process) in period")
            
            # Get payments already included in statements to avoid duplicates
            existing_statement_lines = self.env['account.bank.statement.line'].search([
                ('statement_id.journal_id', '=', record.journal_id.id),
                ('move_id', '!=', False),
            ])
            
            # Get move IDs already used in statement lines
            used_move_ids = set()
            for line in existing_statement_lines:
                if line.move_id:
                    used_move_ids.add(line.move_id.id)
            
            _logger.info(f"Found {len(used_move_ids)} move IDs already used in statements")
            
            # Filter out payments already included in statements
            available_payments = credit_card_payments.filtered(
                lambda p: not p.move_id or p.move_id.id not in used_move_ids
            )
            
            _logger.info(f"Available credit card payments after filtering: {len(available_payments)}")
            
            # Separate payments by currency
            ars_payments = 0.0
            usd_payments = 0.0
            
            for payment in available_payments:
                _logger.info(f"Processing credit card payment: {payment.name}, Amount: {payment.amount}, Currency: {payment.currency_id.name if payment.currency_id else 'Company Currency'}")
                
                if payment.currency_id and payment.currency_id.name == 'ARS':
                    ars_payments += payment.amount
                elif payment.currency_id and payment.currency_id.name == 'USD':
                    usd_payments += payment.amount
                else:
                    # Default to ARS if no currency
                    ars_payments += payment.amount
            
            record.payments_ars = ars_payments
            record.payments_usd = usd_payments
            
            _logger.info(f"Final credit card payments - ARS: {ars_payments}, USD: {usd_payments}")
    
    @api.depends('payments_ars', 'payments_usd', 'state')
    def _compute_payments_total(self):
        """Calculate total payments to credit card"""
        for record in self:
            record.payments_total = record.payments_ars + record.payments_usd
    
    @api.depends('journal_id', 'state', 'closing_date')
    def _compute_previous_balance(self):
        """Calculate previous balance from the last closed statement total"""
        for record in self:
            if not record.journal_id:
                record.previous_balance = 0.0
                continue
                
            # Find the most recent closed credit card statement
            last_statement = self.env['account.bank.statement'].search([
                ('journal_id', '=', record.journal_id.id),
                ('is_credit_card_statement', '=', True),
                ('date', '<', record.closing_date) if record.closing_date else ('id', '!=', False),
            ], order='date desc', limit=1)
            
            if last_statement and hasattr(last_statement, 'statement_total_general') and last_statement.statement_total_general:
                # Use the total from the last closed statement
                record.previous_balance = last_statement.statement_total_general
                _logger.info(f"Previous balance from last statement {last_statement.name}: {record.previous_balance}")
            else:
                # Fallback: if no previous statement, start with 0
                record.previous_balance = 0.0
                _logger.info("No previous statement found, starting balance: 0.0")
    
    @api.depends('journal_id')
    def _compute_last_statement_info(self):
        """Get information from the last generated statement"""
        for record in self:
            if not record.journal_id:
                record.last_closing_date = False
                record.last_due_date = False
                continue
                
            # Find the most recent statement for this journal
            last_statement = self.env['account.bank.statement'].search([
                ('journal_id', '=', record.journal_id.id),
            ], order='date desc', limit=1)
            
            if last_statement and last_statement.date:
                record.last_closing_date = last_statement.date
                # Try to get due date from statement lines (if stored there)
                # For now, estimate 30 days after closing
                record.last_due_date = fields.Date.add(last_statement.date, days=30)
            else:
                record.last_closing_date = False
                record.last_due_date = False

    @api.onchange('closing_date')
    def _onchange_closing_date(self):
        """Auto-calculate due date (30 days after closing)"""
        if self.closing_date:
            self.due_date = fields.Date.add(self.closing_date, days=30)
    
    def check_payment_states(self):
        """Debug method to check what payment states exist"""
        payments = self.env['account.payment'].search([
            ('journal_id', '=', self.journal_id.id),
        ])
        
        states = {}
        for payment in payments:
            state = payment.state
            if state not in states:
                states[state] = 0
            states[state] += 1
            
        _logger.info(f"Payment states found in journal {self.journal_id.name}: {states}")
        
        # Check specifically for payments in the last 30 days
        from datetime import date, timedelta
        recent_date = date.today() - timedelta(days=30)
        recent_payments = payments.filtered(lambda p: p.date >= recent_date)
        
        recent_states = {}
        for payment in recent_payments:
            state = payment.state
            if state not in recent_states:
                recent_states[state] = 0
            recent_states[state] += 1
            
        _logger.info(f"Recent payment states (last 30 days): {recent_states}")
        
        return True

    def _get_outstanding_move_lines(self, start_date, end_date):
        """Get all outstanding move lines (consumptions and payments) for the period"""
        if not self.journal_id.default_account_id:
            _logger.error(f"Journal {self.journal_id.name} has no default_account_id configured!")
            return self.env['account.move.line']
        
        # Get all outstanding move lines for this account in the period
        outstanding_move_lines = self.env['account.move.line'].search([
            ('account_id', '=', self.journal_id.default_account_id.id),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('reconciled', '=', False),  # Only unreconciled (outstanding) entries
            ('move_id.state', '=', 'posted'),  # Only posted moves
            '|',
            ('debit', '>', 0),  # Payments to credit card
            ('credit', '>', 0),  # Consumptions with credit card
        ])
        
        _logger.info(f"Found {len(outstanding_move_lines)} outstanding move lines between {start_date} and {end_date}")
        
        # Filter out move lines already included in statements
        existing_statement_lines = self.env['account.bank.statement.line'].search([
            ('statement_id.journal_id', '=', self.journal_id.id),
            ('move_id', '!=', False),
        ])
        
        used_move_ids = set()
        for line in existing_statement_lines:
            if line.move_id:
                used_move_ids.add(line.move_id.id)
        
        available_move_lines = outstanding_move_lines.filtered(
            lambda ml: ml.move_id.id not in used_move_ids
        )
        
        _logger.info(f"Available move lines after filtering duplicates: {len(available_move_lines)}")
        
        return available_move_lines

    def _get_in_process_payments(self, start_date, end_date):
        """Get all in_process payments for the period (consumptions and credit card payments)"""
        
        # Get consumption payments (FROM this credit card)
        consumption_payments = self.env['account.payment'].search([
            ('journal_id', '=', self.journal_id.id),
            ('state', '=', 'in_process'),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('payment_type', '=', 'outbound'),
        ])
        
        # Get credit card payments (TO this credit card)
        credit_card_payments = self.env['account.payment'].search([
            ('destination_journal_id', '=', self.journal_id.id),
            ('state', '=', 'in_process'),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('payment_type', '=', 'outbound'),
        ])
        
        # Combine both types
        all_payments = consumption_payments | credit_card_payments
        
        _logger.info(f"Found {len(consumption_payments)} consumption payments and {len(credit_card_payments)} credit card payments")
        _logger.info(f"Total in_process payments: {len(all_payments)}")
        
        # Filter out payments already included in statements
        existing_statement_lines = self.env['account.bank.statement.line'].search([
            ('statement_id.journal_id', '=', self.journal_id.id),
            ('move_id', '!=', False),
        ])
        
        used_move_ids = set()
        for line in existing_statement_lines:
            if line.move_id:
                used_move_ids.add(line.move_id.id)
        
        available_payments = all_payments.filtered(
            lambda p: not p.move_id or p.move_id.id not in used_move_ids
        )
        
        _logger.info(f"Available in_process payments after filtering duplicates: {len(available_payments)}")
        
        return available_payments

    def _get_available_payments(self, start_date, end_date):
        """Get payments not already included in other statements"""
        # Get all payments in the period - focus on in_process and posted states
        all_payments = self.env['account.payment'].search([
            ('journal_id', '=', self.journal_id.id),
            ('state', 'in', ['posted', 'in_process']),  # Focus on these key states
            ('date', '>=', start_date),
            ('date', '<=', end_date),
        ])
        
        # Debug: Log what we found with more detail
        _logger.info(f"Found {len(all_payments)} payments for journal {self.journal_id.name} between {start_date} and {end_date}")
        for payment in all_payments:
            _logger.info(f"Payment: {payment.name}, State: {payment.state}, Amount: {payment.amount}, Date: {payment.date}, Partner: {payment.partner_id.name if payment.partner_id else 'No Partner'}")
        
        # Get payments already included in ANY statements (not just current period)
        existing_statement_lines = self.env['account.bank.statement.line'].search([
            ('statement_id.journal_id', '=', self.journal_id.id),
            ('move_id', '!=', False),
        ])
        
        # Get all payment identifiers already used in statement lines
        used_payment_names = set()
        used_move_ids = set()
        used_refs = set()
        
        for line in existing_statement_lines:
            # Collect move IDs
            if line.move_id:
                used_move_ids.add(line.move_id.id)
            # Collect payment names from line names (extract payment number)
            if line.name:
                # Extract payment number from label format "PAYMENT_NUMBER - Partner Name"
                payment_name = line.name.split(' - ')[0] if ' - ' in line.name else line.name
                used_payment_names.add(payment_name)
            # Collect refs
            if line.ref:
                used_refs.add(line.ref)
        
        _logger.info(f"Found {len(used_move_ids)} used move IDs, {len(used_payment_names)} used payment names, and {len(used_refs)} used refs")
        
        # Filter out payments that are already imported
        available_payments = all_payments.filtered(
            lambda p: (
                # Not already imported by move_id
                (not p.move_id or p.move_id.id not in used_move_ids) and
                # Not already imported by payment name
                (not p.name or p.name not in used_payment_names) and
                # Not already imported by ref
                (not p.name or p.name not in used_refs)
            )
        )
        
        _logger.info(f"Available payments after filtering: {len(available_payments)}")
        
        return available_payments
    
    def _get_previous_statement_ending_balance(self):
        """Get account balance BEFORE this statement period to avoid double counting"""
        if not self.journal_id or not self.journal_id.default_account_id:
            _logger.info("No journal or default account configured")
            return 0.0
            
        account = self.journal_id.default_account_id
        
        # Calculate the account balance EXCLUDING movements from this statement period
        if self.closing_date:
            # Get the start of the statement period (first day of month)
            start_date = self.closing_date.replace(day=1)
            
            # Get balance BEFORE the statement period starts
            domain = [
                ('account_id', '=', account.id),
                ('move_id.state', '=', 'posted'),
                ('date', '<', start_date),  # Before the statement period
            ]
        else:
            # If no closing date, get current balance
            domain = [
                ('account_id', '=', account.id),
                ('move_id.state', '=', 'posted'),
            ]
        
        move_lines = self.env['account.move.line'].search(domain)
        account_balance = sum(move_lines.mapped('balance'))
        
        _logger.info(f"Starting balance for statement - Account {account.name}:")
        _logger.info(f"  - Statement period starts: {start_date if self.closing_date else 'No date'}")
        _logger.info(f"  - Move lines BEFORE period: {len(move_lines)}")
        _logger.info(f"  - Balance BEFORE period: {account_balance}")
        
        # Return the actual account balance before this statement period
        return account_balance
    
    def action_generate_statement(self):
        """Generate the credit card statement"""
        self.ensure_one()
        
        if not self.journal_id.is_credit_card:
            raise UserError(_("This action is only available for credit card journals."))
        
        # Calculate date range: from last statement closing date + 1 day to current closing date
        last_statement = self.env['account.bank.statement'].search([
            ('journal_id', '=', self.journal_id.id),
            ('is_credit_card_statement', '=', True),
            ('date', '<', self.closing_date),
        ], order='date desc', limit=1)
        
        if last_statement and last_statement.closing_date:
            start_date = last_statement.closing_date + timedelta(days=1)
        else:
            # If no previous statement, use first day of month
            start_date = self.closing_date.replace(day=1)
        
        end_date = self.closing_date
        
        # Get in_process payments for this period  
        in_process_payments = self._get_in_process_payments(start_date, end_date)
        
        _logger.info(f"Generating statement with {len(in_process_payments)} in_process payments")
        
        # Always create a new statement with unique name based on closing date
        _logger.info(f"Creating new statement with {len(in_process_payments)} in_process payments")
        starting_balance = self._get_previous_statement_ending_balance()
        
        # Create unique statement name with timestamp to avoid duplicates
        from datetime import datetime
        timestamp = datetime.now().strftime('%H%M%S')
        statement_name = _('CC Statement %s - %s (%s)') % (
            self.journal_id.name, 
            self.closing_date.strftime('%B %Y'),
            timestamp
        )
        
        statement_vals = {
            'name': statement_name,
            'journal_id': self.journal_id.id,
            'date': self.closing_date,
            'balance_start': starting_balance,
            'balance_end_real': self.journal_id._get_credit_card_balance(),
            # Credit card statement specific fields
            'closing_date': self.closing_date,
            'due_date': self.due_date,
            'is_credit_card_statement': True,
        }
        statement = self.env['account.bank.statement'].create(statement_vals)
        
        # Store reference to created statement
        self.statement_id = statement.id
        
        # Cache the calculated consumption values for later steps
        self.cached_consumptions_ars = self.consumptions_ars
        self.cached_consumptions_usd = self.consumptions_usd
        self.cached_consumptions_total = self.consumptions_total
        
        _logger.info(f"Cached consumptions - ARS: {self.cached_consumptions_ars}, USD: {self.cached_consumptions_usd}, Total: {self.cached_consumptions_total}")
        
        # Create statement lines from outstanding move lines
        line_vals_list = []
        running_balance = 0
        
        # Add in_process payment transactions
        _logger.info(f"Processing {len(in_process_payments)} in_process payments for statement lines...")
        for payment in in_process_payments.sorted('date'):
            # Get the amount in company currency (ARS)
            ars_amount = payment.amount
            
            # Determine if this is a consumption or payment to credit card
            if payment.journal_id.id == self.journal_id.id:
                # This is a consumption (payment FROM credit card)
                amount = -abs(ars_amount)  # Negative = increases debt
                partner_name = payment.partner_id.name if payment.partner_id else 'Credit Card Purchase'
                label = f'{payment.name} - {partner_name}'
                transaction_tag = f'Consumo con Tarjeta'
                _logger.info(f"Consumption payment: {payment.name}, Amount: {amount}")
                
            elif payment.destination_journal_id and payment.destination_journal_id.id == self.journal_id.id:
                # This is a payment TO credit card
                amount = abs(ars_amount)  # Positive = reduces debt
                partner_name = payment.partner_id.name if payment.partner_id else 'Credit Card Payment'
                label = f'{payment.name} - {partner_name}'
                transaction_tag = f'Pago a Tarjeta'
                _logger.info(f"Credit card payment: {payment.name}, Amount: {amount}")
                
            else:
                # Skip payments that don't belong to this credit card
                _logger.warning(f"Skipping payment {payment.name} - not related to this credit card")
                continue
            
            running_balance += amount
            
            line_vals_list.append({
                'name': label,
                'date': payment.date,
                'amount': amount,
                'partner_id': payment.partner_id.id if payment.partner_id else False,
                'ref': payment.name,
                'statement_id': statement.id,
                'payment_ref': payment.name,
            })
        
        # Create all statement lines
        if line_vals_list:
            created_lines = self.env['account.bank.statement.line'].create(line_vals_list)
            _logger.info(f"Successfully created {len(line_vals_list)} statement lines")
            # Debug: Log transaction tags for expense lines
            for line in created_lines:
                if line.payment_ref:
                    _logger.info(f"Created line: {line.name} with tag: {line.payment_ref}")
        elif len(in_process_payments) > 0:
            _logger.warning(f"No lines created despite having {len(in_process_payments)} payments available!")
        
        # Update statement balance
        if statement.balance_start == 0:  # Only update if not already set
            statement.balance_start = self._get_previous_statement_ending_balance()
        statement.balance_end_real = statement.balance_start + running_balance
        
        _logger.info(f"Statement {statement.name} completed with balance: {running_balance}")
        
        # NOTE: Charges are NOT added here automatically - they are added in action_add_charges()
        # This separates the import step from the charges step clearly
        
        # Move to charges state after generating statement
        self.state = 'charges'
        self._recompute_totals()
        return self._return_wizard()

    def action_add_charges(self):
        """Add only the charges/expenses to the current statement"""
        _logger.info("=== ACTION ADD CHARGES ===")
        
        # Use the statement created by this wizard
        statement = self.statement_id
        
        if not statement:
            # Fallback: Find the most recent statement for this journal
            statement = self.env['account.bank.statement'].search([
                ('journal_id', '=', self.journal_id.id),
            ], order='date desc', limit=1)
            
            if not statement:
                raise UserError(_('No se encontró un extracto bancario para agregar gastos. Primero genera un nuevo resumen.'))
            
            # Store reference for future use
            self.statement_id = statement.id
        
        # Create lines for charges only
        line_vals_list = []
        
        # Add taxes if any
        if self.taxes_amount > 0:
            line_vals_list.append({
                'name': _('Impuestos del Resumen'),
                'date': self.closing_date,
                'amount': -self.taxes_amount,
                'partner_id': False,
                'ref': _('Statement Charges'),
                'statement_id': statement.id,
                'payment_ref': 'Impuestos',
            })
        
        # Add interest if any
        if self.interest_amount > 0:
            line_vals_list.append({
                'name': _('Intereses del Resumen'),
                'date': self.closing_date,
                'amount': -self.interest_amount,
                'partner_id': False,
                'ref': _('Statement Charges'),
                'statement_id': statement.id,
                'payment_ref': 'Intereses',
            })
        
        # Add stamps if any
        if self.stamp_amount > 0:
            line_vals_list.append({
                'name': _('Sellados del Resumen'),
                'date': self.closing_date,
                'amount': -self.stamp_amount,
                'partner_id': False,
                'ref': _('Statement Charges'),
                'statement_id': statement.id,
                'payment_ref': 'Sellados',
            })
        
        # Add other charges if any
        if self.other_charges_amount > 0:
            line_vals_list.append({
                'name': _('Otros Gastos del Resumen'),
                'date': self.closing_date,
                'amount': -self.other_charges_amount,
                'partner_id': False,
                'ref': _('Statement Charges'),
                'statement_id': statement.id,
                'payment_ref': 'Otros Gastos',
            })
        
        # Create the charge lines
        if line_vals_list:
            created_lines = self.env['account.bank.statement.line'].create(line_vals_list)
            _logger.info(f"Added {len(line_vals_list)} charge lines to statement {statement.name}")
            # Debug: Log transaction tags
            for line in created_lines:
                _logger.info(f"Created line: {line.name} with tag: {line.payment_ref}")
            
            # Move to close state after adding charges
            self.state = 'close'
            self._recompute_totals()
            return self._return_wizard()
        else:
            raise UserError(_('No hay gastos para agregar. Ingresa valores en Impuestos, Intereses, Sellados u Otros Gastos.'))

    # State navigation methods
    def action_next_import_to_charges(self):
        """Move from import state to charges state"""
        self.state = 'charges'
        self._recompute_totals()
        return self._return_wizard()
    
    def action_next_charges_to_close(self):
        """Move from charges state to close state"""
        self.state = 'close'
        self._recompute_totals()
        return self._return_wizard()
    
    def action_back_to_import(self):
        """Go back to import state"""
        self.state = 'import'
        self._recompute_totals()
        return self._return_wizard()
    
    def action_back_to_charges(self):
        """Go back to charges state"""
        self.state = 'charges'
        self._recompute_totals()
        return self._return_wizard()
    
    def _recompute_totals(self):
        """Force recomputation of all calculated fields"""
        _logger.info("=== RECOMPUTING TOTALS ===")
        self._compute_previous_balance()
        self._compute_consumptions_total()
        self._compute_consumptions_by_currency()
        self._compute_payments_by_currency()
        self._compute_payments_total()
        self._compute_total_charges()
        self._compute_total_to_pay_by_currency()
        self._compute_total_to_pay()
        
        # Debug logging
        _logger.info(f"Previous Balance: {self.previous_balance}")
        _logger.info(f"Consumptions ARS: {self.consumptions_ars}")
        _logger.info(f"Consumptions USD: {self.consumptions_usd}")
        _logger.info(f"Payments ARS: {self.payments_ars}")
        _logger.info(f"Payments USD: {self.payments_usd}")
        _logger.info(f"Total Charges: {self.total_charges}")
        _logger.info(f"Total to Pay ARS: {self.total_to_pay_ars}")
        _logger.info(f"Total to Pay USD: {self.total_to_pay_usd}")
        _logger.info(f"Total to Pay General: {self.total_to_pay}")
        _logger.info("=== END RECOMPUTING TOTALS ===")
    
    def _return_wizard(self):
        """Return action to keep wizard open"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generar Resumen Personalizado de Tarjeta de Crédito'),
            'res_model': 'credit.card.statement.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_close_statement(self):
        """Close the statement - mark it as final and update balances"""
        _logger.info("=== ACTION CLOSE STATEMENT ===")
        
        # Use the statement created by this wizard
        statement = self.statement_id
        
        if not statement:
            # Fallback: Find the most recent statement for this journal
            statement = self.env['account.bank.statement'].search([
                ('journal_id', '=', self.journal_id.id),
            ], order='date desc', limit=1)
            
            if not statement:
                raise UserError(_('No se encontró un extracto bancario para cerrar. Primero genera un nuevo resumen.'))
            
            # Store reference for future use
            self.statement_id = statement.id
        
        # Get the actual account balance from the credit card account
        account_balance = self.journal_id._get_credit_card_balance()
        
        # For credit card statements, ending balance should equal the debt amount (total to pay)
        # This represents the outstanding balance that needs to be paid
        ending_balance = self.total_to_pay
        
        # Save all the calculated values
        statement.write({
            'statement_total_ars': self.total_to_pay_ars,
            'statement_total_usd': self.total_to_pay_usd,
            'statement_total_general': self.total_to_pay,
            'debt_ars': self.total_to_pay_ars,
            'debt_usd': self.total_to_pay_usd,
            'balance_end_real': ending_balance,  # Set ending balance = debt amount
            'account_balance': account_balance,  # Store actual account balance
        })
        
        # ENHANCED: Automatic reconciliation of statement lines
        self._auto_reconcile_statement_lines(statement)
        
        # Mark statement as validated/closed if there's such a state
        if hasattr(statement, 'state') and 'confirm' in statement._fields.get('state', {}).get('selection', []):
            statement.state = 'confirm'
        
        _logger.info(f"Statement {statement.name} closed:")
        _logger.info(f"  - Ending Balance (Debt): {ending_balance}")
        _logger.info(f"  - Account Balance: {account_balance}")
        _logger.info(f"  - Totals - ARS: {self.total_to_pay_ars}, USD: {self.total_to_pay_usd}, General: {self.total_to_pay}")
        
        return {
            'name': _('Credit Card Statement - %s') % self.journal_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement',
            'view_mode': 'form',
            'res_id': statement.id,
            'target': 'current',
        }
    
    def _auto_reconcile_statement_lines(self, statement):
        """Automatically reconcile statement lines with corresponding account moves"""
        _logger.info("=== AUTO RECONCILING STATEMENT LINES ===")
        
        for line in statement.line_ids:
            if line.move_id:
                _logger.info(f"Line {line.name} already has move_id: {line.move_id.name}")
                continue
                
            # Try to find corresponding payment by payment_ref (which stores payment name)
            if line.payment_ref and not line.payment_ref.startswith(('Impuestos', 'Intereses', 'Sellados', 'Otros Gastos')):
                payment = self.env['account.payment'].search([
                    ('name', '=', line.payment_ref),
                    ('journal_id', '=', statement.journal_id.id),
                ], limit=1)
                
                if not payment:
                    # Also try destination_journal_id for credit card payments
                    payment = self.env['account.payment'].search([
                        ('name', '=', line.payment_ref),
                        ('destination_journal_id', '=', statement.journal_id.id),
                    ], limit=1)
                
                if payment and payment.move_id:
                    # Link the statement line to the payment's move
                    line.move_id = payment.move_id.id
                    _logger.info(f"Linked statement line {line.name} to payment move {payment.move_id.name}")
                    
                    # Auto-reconcile if both have the same account
                    credit_card_account = statement.journal_id.default_account_id
                    if credit_card_account:
                        # Find move lines for this account in the payment
                        payment_move_lines = payment.move_id.line_ids.filtered(
                            lambda ml: ml.account_id == credit_card_account and not ml.reconciled
                        )
                        
                        # Find move lines for this account in the statement line
                        statement_move_lines = line.move_id.line_ids.filtered(
                            lambda ml: ml.account_id == credit_card_account and not ml.reconciled
                        ) if line.move_id else self.env['account.move.line']
                        
                        # Reconcile matching lines
                        if payment_move_lines and statement_move_lines:
                            all_lines = payment_move_lines | statement_move_lines
                            # Only reconcile if total balance is zero or close to zero
                            total_balance = sum(all_lines.mapped('balance'))
                            if abs(total_balance) < 0.01:  # Allow small rounding differences
                                all_lines.reconcile()
                                _logger.info(f"Reconciled move lines for {line.name}")
                            else:
                                _logger.warning(f"Cannot reconcile {line.name} - balance mismatch: {total_balance}")
                else:
                    _logger.warning(f"No payment found for statement line {line.name} with ref {line.payment_ref}")
            else:
                # For charges (taxes, interest, etc.), create move lines if needed
                if line.payment_ref and line.payment_ref.startswith(('Impuestos', 'Intereses', 'Sellados', 'Otros Gastos')):
                    _logger.info(f"Statement charge line {line.name} - no reconciliation needed")
        
        _logger.info("=== END AUTO RECONCILING STATEMENT LINES ===")