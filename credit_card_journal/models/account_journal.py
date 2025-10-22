# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    last_closing_date = fields.Date(
        string='Última Fecha de Cierre',
        compute='_compute_last_statement_dates',
        store=False
    )
    last_due_date = fields.Date(
        string='Última Fecha de Vencimiento',
        compute='_compute_last_statement_dates',
        store=False
    )
    company_currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string='Company Currency',
        readonly=True
    )

    @api.depends('is_credit_card')
    def _compute_last_statement_dates(self):
        """Get dates from the last generated statement"""
        for journal in self:
            if not journal.is_credit_card:
                journal.last_closing_date = False
                journal.last_due_date = False
                continue
                
            # Find the most recent statement for this journal
            last_statement = self.env['account.bank.statement'].search([
                ('journal_id', '=', journal.id),
            ], order='date desc', limit=1)
            
            if last_statement and last_statement.date:
                journal.last_closing_date = last_statement.date
                # Calculate due date (30 days after closing)
                journal.last_due_date = fields.Date.add(last_statement.date, days=30)
            else:
                journal.last_closing_date = False
                journal.last_due_date = False

    def action_pay_credit_card(self):
        """Open credit card payment wizard"""
        self.ensure_one()
        
        if not self.is_credit_card:
            raise UserError(_("This action is only available for credit card journals."))
        
        return {
            'name': _('Pay Credit Card'),
            'type': 'ir.actions.act_window',
            'res_model': 'credit.card.payment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_journal_id': self.id,
            },
        }

    def action_issue_credit_card_statement(self):
        """Generate and show credit card statement automatically importing available transactions"""
        self.ensure_one()
        
        if not self.is_credit_card:
            raise UserError(_("This action is only available for credit card journals."))
        
        # Calculate default dates
        today = fields.Date.today()
        closing_date = today
        due_date = fields.Date.add(today, days=30)
        
        # Calculate date range for transactions (from first day of month to today)
        start_date = closing_date.replace(day=1)
        end_date = closing_date
        
        # Check if there's already a statement for this period
        existing_statement = self.env['account.bank.statement'].search([
            ('journal_id', '=', self.id),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
        ], limit=1)
        
        if existing_statement:
            # Show existing statement
            return {
                'name': _('Credit Card Statement - %s') % self.name,
                'type': 'ir.actions.act_window',
                'res_model': 'account.bank.statement',
                'view_mode': 'form',
                'res_id': existing_statement.id,
                'target': 'current',
            }
        
        # Auto-generate statement with available transactions
        return self._auto_generate_statement(closing_date, due_date)

    def _auto_generate_statement(self, closing_date, due_date):
        """Automatically generate statement with available transactions"""
        self.ensure_one()
        
        # Calculate date range - use a wider range to catch all in_process payments
        # Go back 3 months to catch any pending transactions
        start_date = (closing_date.replace(day=1) - timedelta(days=90))
        end_date = closing_date
        
        # Get available payments not already included in other statements
        available_payments = self._get_available_payments_for_statement(start_date, end_date)
        
        _logger.info(f"Auto-generating statement for {self.name} with {len(available_payments)} transactions from {start_date} to {end_date}")
        
        # Create bank statement
        statement_vals = {
            'name': _('CC Statement %s - %s') % (self.name, closing_date.strftime('%B %Y')),
            'journal_id': self.id,
            'date': closing_date,
            'balance_start': 0,
            'balance_end_real': self._get_credit_card_balance(),
        }
        
        statement = self.env['account.bank.statement'].create(statement_vals)
        
        # Create statement lines from available payments
        self._create_statement_lines_from_payments(statement, available_payments)
        
        # Show the generated statement
        return {
            'name': _('Credit Card Statement - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement',
            'view_mode': 'form',
            'res_id': statement.id,
            'target': 'current',
        }

    def _get_available_payments_for_statement(self, start_date, end_date):
        """Get payments not already included in other statements"""
        # Get all payments in the period - focus on in_process and posted states
        all_payments = self.env['account.payment'].search([
            ('journal_id', '=', self.id),
            ('state', 'in', ['posted', 'in_process']),  # Focus on these states
            ('date', '>=', start_date),
            ('date', '<=', end_date),
        ])
        
        # Debug: Log what we found with details
        _logger.info(f"Found {len(all_payments)} payments for journal {self.name} between {start_date} and {end_date}")
        for payment in all_payments:
            _logger.info(f"Payment: {payment.name}, State: {payment.state}, Amount: {payment.amount}, Partner: {payment.partner_id.name if payment.partner_id else 'No Partner'}")
        
        # Get payments already included in other statements
        existing_statement_lines = self.env['account.bank.statement.line'].search([
            ('statement_id.journal_id', '=', self.id),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('move_id', '!=', False),
        ])
        
        # Get move IDs from existing statement lines
        used_move_ids = existing_statement_lines.mapped('move_id').ids
        
        # Filter out payments whose moves are already in statements
        available_payments = all_payments.filtered(
            lambda p: not p.move_id or p.move_id.id not in used_move_ids
        )
        
        _logger.info(f"Available payments after filtering: {len(available_payments)}")
        
        return available_payments

    def _create_statement_lines_from_payments(self, statement, payments):
        """Create statement lines from payments with simple transaction tags"""
        line_vals_list = []
        
        for payment in payments.sorted('date'):
            # For credit card statement: ALL payments from suppliers/vendors should be NEGATIVE (debt)
            # Only payments TO the credit card company should be POSITIVE (reducing debt)
            
            if payment.partner_id and payment.partner_id.supplier_rank > 0:
                # Supplier payment = expense with credit card = NEGATIVE
                amount = -payment.amount
                partner_name = payment.partner_id.name
                label = _('Purchase: %s') % partner_name
                transaction_tag = 'Compra a Proveedor'
            elif payment.payment_type == 'inbound':
                # Other inbound payments = expenses = NEGATIVE  
                amount = -payment.amount
                partner_name = payment.partner_id.name if payment.partner_id else 'Credit Card Purchase'
                label = _('Purchase: %s') % partner_name
                transaction_tag = 'Gasto con Tarjeta'
            else:  # outbound to credit card company
                # Payment to credit card = POSITIVE (reducing debt)
                amount = payment.amount
                partner_name = payment.partner_id.name if payment.partner_id else 'Credit Card Payment'
                label = _('Payment: %s') % partner_name
                transaction_tag = 'Pago de Tarjeta'
            
            line_vals_list.append({
                'name': label,
                'date': payment.date,
                'amount': amount,
                'partner_id': payment.partner_id.id if payment.partner_id else False,
                'ref': payment.name,
                'statement_id': statement.id,
                'payment_ref': transaction_tag,
            })
        
        # Create all statement lines
        if line_vals_list:
            self.env['account.bank.statement.line'].create(line_vals_list)
            _logger.info(f"Created {len(line_vals_list)} statement lines for {statement.name}")

    def action_custom_credit_card_statement(self):
        """Open wizard for custom credit card statement generation"""
        self.ensure_one()
        
        if not self.is_credit_card:
            raise UserError(_("This action is only available for credit card journals."))
        
        return {
            'name': _('Generar Resumen Personalizado de Tarjeta de Crédito'),
            'type': 'ir.actions.act_window',
            'res_model': 'credit.card.statement.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_journal_id': self.id,
            },
        }

    def action_view_credit_card_statements(self):
        """View credit card statements for this journal"""
        self.ensure_one()
        
        if not self.is_credit_card:
            raise UserError(_("This action is only available for credit card journals."))
        
        return {
            'name': _('Credit Card Statements - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('credit_card_journal.view_bank_statement_tree_credit_card').id, 'list'),
                (self.env.ref('account_accountant.view_bank_statement_form_bank_rec_widget').id, 'form')
            ],
            'domain': [
                ('journal_id', '=', self.id),
                ('is_credit_card_statement', '=', True)
            ],
            'context': {
                'default_journal_id': self.id,
                'default_is_credit_card_statement': True,
            },
            'target': 'current',
        }

    def _get_credit_card_balance(self):
        """Get current credit card running balance from dashboard"""
        self.ensure_one()
        
        if not self.is_credit_card:
            return 0.0
            
        # Get the running balance from the journal dashboard
        # This uses the same calculation as the standard Odoo dashboard
        if hasattr(self, '_get_journal_dashboard_datas'):
            dashboard_data = self._get_journal_dashboard_datas()
            # The dashboard provides the account balance
            if 'account_balance' in dashboard_data:
                return dashboard_data['account_balance']
        
        # Fallback to manual calculation if dashboard method not available
        moves = self.env['account.move.line'].search([
            ('journal_id', '=', self.id),
            ('move_id.state', '=', 'posted'),
            ('account_id', '=', self.default_account_id.id),
        ])
        
        return sum(moves.mapped('balance'))

    def _get_payment_journal_id(self):
        """Get the default journal for payments (usually bank or cash)"""
        payment_journal = self.env['account.journal'].search([
            ('type', 'in', ['bank', 'cash']),
            ('company_id', '=', self.company_id.id),
            ('id', '!=', self.id),
        ], limit=1)
        
        if not payment_journal:
            raise UserError(_("No payment journal found. Please configure a bank or cash journal."))
        
        return payment_journal.id

    is_credit_card = fields.Boolean(
        string="Is Credit Card",
        default=False,
        help="Check this box if this is a credit card journal"
    )
    
    credit_card_balance = fields.Monetary(
        string="Credit Card Balance",
        compute="_compute_credit_card_balance",
        currency_field="currency_id",
        help="Current balance of the credit card"
    )
    
    # Account balance (saldo de la cuenta contable)
    account_balance = fields.Monetary(
        string="Account Balance",
        compute="_compute_account_balance",
        currency_field="currency_id",
        help="Current balance of the default account"
    )
    
    # Totals from latest statement
    total_to_pay_ars = fields.Monetary(
        string="Total to Pay (ARS)",
        compute="_compute_payment_totals",
        currency_field="company_currency_id",
        help="Total amount to pay in ARS from latest statement"
    )
    
    total_to_pay_usd = fields.Monetary(
        string="Total to Pay (USD)",
        compute="_compute_payment_totals", 
        currency_field="currency_id",
        help="Total amount to pay in USD from latest statement"
    )
    
    # Outstanding consumptions (not yet in any statement)
    outstanding_consumptions_ars = fields.Monetary(
        string="Outstanding Consumptions (ARS)",
        compute="_compute_outstanding_consumptions",
        currency_field="company_currency_id",
        help="Consumptions in ARS not yet included in any statement"
    )
    
    outstanding_consumptions_usd = fields.Monetary(
        string="Outstanding Consumptions (USD)",
        compute="_compute_outstanding_consumptions",
        currency_field="currency_id",
        help="Consumptions in USD not yet included in any statement"
    )
    
    # Outstanding payments to credit card (not yet in any statement)
    outstanding_payments_ars = fields.Monetary(
        string="Outstanding Payments (ARS)",
        compute="_compute_outstanding_payments",
        currency_field="company_currency_id",
        help="Payments to credit card in ARS not yet included in any statement"
    )
    
    outstanding_payments_usd = fields.Monetary(
        string="Outstanding Payments (USD)",
        compute="_compute_outstanding_payments",
        currency_field="currency_id",
        help="Payments to credit card in USD not yet included in any statement"
    )
    
    @api.depends('default_account_id')
    def _compute_credit_card_balance(self):
        """Compute credit card balance"""
        for journal in self:
            if journal.is_credit_card and journal.default_account_id:
                journal.credit_card_balance = journal._get_credit_card_balance()
            else:
                journal.credit_card_balance = 0.0
    
    @api.depends('default_account_id')
    def _compute_account_balance(self):
        """Compute the current balance of the default account"""
        for journal in self:
            if journal.default_account_id:
                journal.account_balance = journal._get_credit_card_balance()
            else:
                journal.account_balance = 0.0
    
    @api.depends('is_credit_card')
    def _compute_payment_totals(self):
        """Compute payment totals from latest statement"""
        for journal in self:
            if not journal.is_credit_card:
                journal.total_to_pay_ars = 0
                journal.total_to_pay_usd = 0
                continue
                
            # Get latest statement wizard data
            try:
                latest_wizard = self.env['credit.card.statement.wizard'].search([
                    ('journal_id', '=', journal.id)
                ], order='closing_date desc', limit=1)
                
                if latest_wizard:
                    # Use .read() to avoid computed field recursion
                    wizard_data = latest_wizard.read(['total_to_pay_ars', 'total_to_pay_usd'])[0] if latest_wizard else {}
                    journal.total_to_pay_ars = wizard_data.get('total_to_pay_ars', 0) or 0
                    journal.total_to_pay_usd = wizard_data.get('total_to_pay_usd', 0) or 0
                else:
                    journal.total_to_pay_ars = 0
                    journal.total_to_pay_usd = 0
            except Exception:
                # Fallback in case of any issues
                journal.total_to_pay_ars = 0
                journal.total_to_pay_usd = 0
    
    @api.depends('is_credit_card')
    def _compute_outstanding_consumptions(self):
        """Compute outstanding consumptions not yet included in any statement"""
        for journal in self:
            if not journal.is_credit_card:
                journal.outstanding_consumptions_ars = 0
                journal.outstanding_consumptions_usd = 0
                continue
            
            # Get all consumption payments (in_process) from this credit card
            consumption_payments = self.env['account.payment'].search([
                ('journal_id', '=', journal.id),
                ('state', '=', 'in_process'),
                ('payment_type', '=', 'outbound'),
                ('partner_id.supplier_rank', '>', 0),  # Only supplier payments
            ])
            
            # Get payments already included in statements
            existing_statement_lines = self.env['account.bank.statement.line'].search([
                ('statement_id.journal_id', '=', journal.id),
                ('payment_ref', 'in', consumption_payments.mapped('name')),
            ])
            
            # Get payment names already used in statement lines
            used_payment_names = set(existing_statement_lines.mapped('payment_ref'))
            
            # Filter out payments already included in statements
            outstanding_payments = consumption_payments.filtered(
                lambda p: p.name not in used_payment_names
            )
            
            # Separate by currency
            ars_total = 0.0
            usd_total = 0.0
            
            for payment in outstanding_payments:
                if payment.currency_id and payment.currency_id.name == 'USD':
                    usd_total += payment.amount
                elif payment.currency_id and payment.currency_id.name == 'ARS':
                    ars_total += payment.amount
                else:
                    # Default to company currency
                    company_currency = journal.company_id.currency_id
                    if company_currency.name == 'USD':
                        usd_total += payment.amount
                    else:
                        ars_total += payment.amount
            
            journal.outstanding_consumptions_ars = ars_total
            journal.outstanding_consumptions_usd = usd_total
    
    @api.depends('is_credit_card')
    def _compute_outstanding_payments(self):
        """Compute outstanding payments TO credit card not yet included in any statement"""
        for journal in self:
            if not journal.is_credit_card:
                journal.outstanding_payments_ars = 0
                journal.outstanding_payments_usd = 0
                continue
            
            # Get all payments TO this credit card (in_process)
            credit_card_payments = self.env['account.payment'].search([
                ('destination_journal_id', '=', journal.id),
                ('state', '=', 'in_process'),
                ('payment_type', '=', 'outbound'),
            ])
            
            # Get payments already included in statements
            existing_statement_lines = self.env['account.bank.statement.line'].search([
                ('statement_id.journal_id', '=', journal.id),
                ('payment_ref', 'in', credit_card_payments.mapped('name')),
            ])
            
            # Get payment names already used in statement lines
            used_payment_names = set(existing_statement_lines.mapped('payment_ref'))
            
            # Filter out payments already included in statements
            outstanding_payments = credit_card_payments.filtered(
                lambda p: p.name not in used_payment_names
            )
            
            # Separate by currency
            ars_total = 0.0
            usd_total = 0.0
            
            for payment in outstanding_payments:
                if payment.currency_id and payment.currency_id.name == 'USD':
                    usd_total += payment.amount
                elif payment.currency_id and payment.currency_id.name == 'ARS':
                    ars_total += payment.amount
                else:
                    # Default to company currency
                    company_currency = journal.company_id.currency_id
                    if company_currency.name == 'USD':
                        usd_total += payment.amount
                    else:
                        ars_total += payment.amount
            
            journal.outstanding_payments_ars = ars_total
            journal.outstanding_payments_usd = usd_total