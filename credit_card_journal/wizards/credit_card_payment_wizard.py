# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CreditCardPaymentWizard(models.TransientModel):
    _name = 'credit.card.payment.wizard'
    _description = 'Credit Card Payment Wizard'
    _check_company_auto = True

    journal_id = fields.Many2one(
        'account.journal',
        string='Credit Card Journal',
        required=True,
        readonly=True
    )
    
    source_journal_id = fields.Many2one(
        'account.journal',
        string='Pay From Journal',
        required=True,
        domain="[('type', 'in', ['bank', 'cash']), ('id', '!=', journal_id)]",
        help="Select the journal from which you want to pay the credit card"
    )
    
    amount = fields.Monetary(
        string='Amount to Pay',
        currency_field='currency_id',
        required=True,
        help="Enter the amount you want to pay (can be partial payment)"
    )
    
    payment_type = fields.Selection([
        ('ars', 'Total en Pesos (ARS)'),
        ('usd', 'Total en Dólares (USD)'),
        ('total', 'Total General (ARS + USD convertido)')
    ], string='Tipo de Pago', default='total', required=True)
    
    # Outstanding debt amounts by currency
    total_ars_debt = fields.Monetary(
        string='Deuda en ARS',
        currency_field='currency_id',
        compute='_compute_debt_totals',
        readonly=True
    )
    total_usd_debt = fields.Monetary(
        string='Deuda en USD',
        currency_field='currency_id',
        compute='_compute_debt_totals',
        readonly=True
    )
    total_general_debt = fields.Monetary(
        string='Total General',
        currency_field='currency_id',
        compute='_compute_debt_totals',
        readonly=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True
    )
    
    credit_card_balance = fields.Monetary(
        string='Current Credit Card Balance',
        currency_field='currency_id',
        readonly=True
    )
    
    payment_date = fields.Date(
        string='Payment Date',
        required=True,
        default=fields.Date.context_today
    )
    
    memo = fields.Char(
        string='Memo',
        default=lambda self: _('Credit Card Payment')
    )

    @api.model
    def default_get(self, fields_list):
        """Set default values from context"""
        res = super().default_get(fields_list)
        
        journal_id = self.env.context.get('default_journal_id')
        if journal_id:
            journal = self.env['account.journal'].browse(journal_id)
            res.update({
                'journal_id': journal_id,
                'currency_id': journal.currency_id.id or journal.company_id.currency_id.id,
                'credit_card_balance': journal._get_credit_card_balance(),
                'amount': abs(journal._get_credit_card_balance()) if journal._get_credit_card_balance() < 0 else 0,
            })
        
        return res

    @api.depends('journal_id')
    def _compute_debt_totals(self):
        """Compute outstanding debt totals from the latest closed statement
        Convention: Negative values = Debt (to pay), Positive = Credit balance"""
        for record in self:
            if not record.journal_id:
                record.total_ars_debt = 0
                record.total_usd_debt = 0
                record.total_general_debt = 0
                continue
            
            # Get the latest closed credit card statement
            latest_statement = self.env['account.bank.statement'].search([
                ('journal_id', '=', record.journal_id.id),
                ('is_credit_card_statement', '=', True),
                ('statement_total_ars', '!=', 0),  # Any statements with saved totals (positive or negative)
            ], order='date desc', limit=1)
            
            if latest_statement:
                # Use data from the latest closed statement
                # Convert negative values (debt) to positive for display
                record.total_ars_debt = abs(latest_statement.debt_ars or latest_statement.statement_total_ars or 0) if (latest_statement.debt_ars or latest_statement.statement_total_ars or 0) < 0 else 0
                record.total_usd_debt = abs(latest_statement.debt_usd or latest_statement.statement_total_usd or 0) if (latest_statement.debt_usd or latest_statement.statement_total_usd or 0) < 0 else 0
                record.total_general_debt = abs(latest_statement.statement_total_general or 0) if (latest_statement.statement_total_general or 0) < 0 else 0
            else:
                # Fallback: try to get from latest statement wizard if no closed statement
                latest_wizard = self.env['credit.card.statement.wizard'].search([
                    ('journal_id', '=', record.journal_id.id)
                ], order='closing_date desc', limit=1)
                
                if latest_wizard:
                    # Convert negative values (debt) to positive for display
                    record.total_ars_debt = abs(latest_wizard.total_to_pay_ars or 0) if (latest_wizard.total_to_pay_ars or 0) < 0 else 0
                    record.total_usd_debt = abs(latest_wizard.total_to_pay_usd or 0) if (latest_wizard.total_to_pay_usd or 0) < 0 else 0
                    record.total_general_debt = abs(latest_wizard.total_to_pay or 0) if (latest_wizard.total_to_pay or 0) < 0 else 0
                else:
                    # Final fallback: calculate from current credit card balance
                    balance = record.journal_id._get_credit_card_balance()
                    if balance < 0:  # Negative balance means debt
                        record.total_ars_debt = abs(balance)
                        record.total_usd_debt = 0
                        record.total_general_debt = abs(balance)
                    else:
                        record.total_ars_debt = 0
                        record.total_usd_debt = 0
                        record.total_general_debt = 0

    @api.onchange('payment_type', 'total_ars_debt', 'total_usd_debt', 'total_general_debt')
    def _onchange_payment_type(self):
        """Set default amount based on payment type selection, but allow manual editing"""
        if self.payment_type == 'ars':
            self.amount = self.total_ars_debt
        elif self.payment_type == 'usd':
            self.amount = self.total_usd_debt
        else:  # 'total'
            self.amount = self.total_general_debt

    def action_create_payment(self):
        """Create internal transfer payment to pay credit card using account_internal_transfer"""
        self.ensure_one()
        
        if self.amount <= 0:
            raise UserError(_("Amount to pay must be greater than zero."))
        
        if not self.source_journal_id:
            raise UserError(_("Please select a source journal to pay from."))
        
        # Validate that both journals are from the same company
        if self.source_journal_id.company_id != self.journal_id.company_id:
            raise UserError(_("Source journal and credit card journal must be from the same company."))
        
        # Determine the correct currency and amount based on payment type
        if self.payment_type == 'usd':
            # For USD payments, use USD currency and user-specified amount
            payment_currency = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
            if not payment_currency:
                raise UserError(_("USD currency not found in system."))
            payment_amount = self.amount  # Use amount from wizard, not total available
            payment_currency_id = payment_currency.id
            
            # Validate that source journal supports USD or can handle multi-currency
            source_currency = self.source_journal_id.currency_id or self.source_journal_id.company_id.currency_id
            if source_currency.name != 'USD' and not self.source_journal_id.company_id.currency_id:
                raise UserError(_("Source journal must support USD currency for USD payments. Please select a USD journal or ensure multi-currency is enabled."))
                
        elif self.payment_type == 'ars':
            # For ARS payments, use company currency (ARS) and user-specified amount
            payment_currency_id = self.journal_id.company_id.currency_id.id
            payment_amount = self.amount  # Use amount from wizard, not total available
        else:  # 'total'
            # For total general, use company currency (ARS) with user-specified amount
            payment_currency_id = self.journal_id.company_id.currency_id.id
            payment_amount = self.amount  # Use amount from wizard, not total available
        
        # Create internal transfer payment using account_internal_transfer module
        payment_vals = {
            'payment_type': 'outbound',
            'journal_id': self.source_journal_id.id,
            'destination_journal_id': self.journal_id.id,
            'amount': payment_amount,
            'currency_id': payment_currency_id,
            'date': self.payment_date,
            'memo': self.memo or _('Credit Card Payment'),
            'is_internal_transfer': True,
            'partner_id': False,  # Internal transfers don't have partners
        }
        
        # Create and post the payment
        payment = self.env['account.payment'].create(payment_vals)
        payment.action_post()
        
        # NOTE: Do NOT create statement line automatically here
        # Statement lines for credit card payments should only be created 
        # through the credit_card_statement_wizard to avoid circular dependencies
        # and ensure proper statement balance continuity
        
        return {
            'name': _('Credit Card Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'view_mode': 'form',
            'res_id': payment.id,
            'target': 'current',
        }

