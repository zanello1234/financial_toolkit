# © 2025 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_credit_card = fields.Boolean(
        string='Is Credit Card Journal',
        default=False,
        help='Mark this journal as a credit card journal'
    )
    
    card_plan_ids = fields.One2many(
        'card.plan',
        'journal_id',
        string='Credit Card Plans',
        help='Available credit card plans for this journal'
    )
    
    transfer_liquidity_account_id = fields.Many2one(
        'account.account',
        string='Transfer Liquidity Account',
        help='Bridge account for liquidity transfers to final bank'
    )
    
    final_bank_journal_id = fields.Many2one(
        'account.journal',
        string='Final Bank Journal',
        domain=[('type', '=', 'bank')],
        help='Final bank journal where the net amount will be transferred'
    )

    @api.onchange('type')
    def _onchange_type(self):
        """Reset credit card flag when changing journal type"""
        if self.type != 'bank':
            self.is_credit_card = False

    def _validate_reconcile_model_compatibility(self):
        """
        Validate that reconcile model operations are compatible with Odoo 18
        In Odoo 18, reconcile models don't have journal_id field
        """
        return True  # Always return True for Odoo 18 compatibility

    def action_open_reconcile_model_config(self):
        """Abre la configuración de modelos de conciliación para este diario"""
        self.ensure_one()
        
        # Validate compatibility first
        self._validate_reconcile_model_compatibility()
        
        try:
            # Try to get the standard action first
            action = self.env.ref('account.action_account_reconcile_model').read()[0]
            
            # Update the action with our specific context (without journal_id domain)
            action.update({
                'name': _('Reconciliation Models - %s') % self.name,
                'context': {
                    'default_rule_type': 'invoice_matching',
                    'create': True,
                    'edit': True,
                },
            })
            
            return action
            
        except ValueError:
            # Fallback to manual action definition if reference doesn't exist
            return {
                'name': _('Reconciliation Models - %s') % self.name,
                'type': 'ir.actions.act_window',
                'res_model': 'account.reconcile.model',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'context': {
                    'default_rule_type': 'invoice_matching',
                    'create': True,
                    'edit': True,
                },
                'target': 'current',
            }

    def create_default_reconcile_models(self):
        """Create default reconcile models for card fees"""
        try:
            if not self.is_credit_card:
                raise UserError(_("This journal is not configured as a credit card journal."))
            
            # Check if reconcile models already exist
            existing_models = self.env['account.reconcile.model'].search([
                ('name', 'ilike', f'Card Fees - {self.name}')
            ])
            
            if existing_models:
                raise UserError(_("Default reconciliation models already exist for this journal."))
            
            # Get or create the default expense account (without company_id filter to avoid issues)
            expense_account = self.env['account.account'].search([
                ('account_type', '=', 'expense'),
                ('name', 'ilike', 'card')
            ], limit=1)
            
            if not expense_account:
                # Try to find any expense account
                expense_account = self.env['account.account'].search([
                    ('account_type', '=', 'expense')
                ], limit=1)
            
            if not expense_account:
                # Create a default card fee expense account
                expense_account = self.env['account.account'].create({
                    'name': 'Card Processing Fees',
                    'code': self._get_next_account_code('6110'),
                    'account_type': 'expense',
                })
            
            # Create reconcile model for card fees
            reconcile_model = self.env['account.reconcile.model'].create({
                'name': f'Card Fees - {self.name}',
                'rule_type': 'writeoff_suggestion',
                'auto_reconcile': False,
                'to_check': True,
                'line_ids': [(0, 0, {
                    'account_id': expense_account.id,
                    'label': 'Card Processing Fee',
                    'amount_type': 'percentage',
                    'amount': 100.0,
                })],
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Default reconciliation models created successfully.'),
                    'type': 'success',
                }
            }
            
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': str(e),
                    'type': 'danger',
                }
            }

    def _get_next_account_code(self, base_code):
        """Get the next available account code"""
        existing_account = self.env['account.account'].search([
            ('code', '=', base_code)
        ])
        
        if not existing_account:
            return base_code
            
        # Find next available code
        counter = 1
        while True:
            new_code = f"{base_code}{counter:02d}"
            if not self.env['account.account'].search([
                ('code', '=', new_code)
            ]):
                return new_code
            counter += 1
            if counter > 99:  # Safety limit
                return f"{base_code}99"

    def action_configure_reconcile_models(self):
        """Open reconcile models configuration for this journal"""
        return {
            'name': _('Reconciliation Models'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.reconcile.model',
            'view_mode': 'list,form',
            'views': [
                (False, 'list'),
                (False, 'form')
            ],
            'domain': [
                ('company_id', '=', self.company_id.id),
                '|',
                ('name', 'ilike', self.name),
                ('name', 'ilike', 'card')
            ],
            'context': {
                'default_company_id': self.company_id.id,
                'search_default_group_by_rule_type': 1,
            },
            'target': 'current',
        }

    def create_default_card_plans(self):
        """Create default card plans for this journal"""
        try:
            if not self.is_credit_card:
                raise UserError(_("This journal is not configured as a credit card journal."))
            
            # Check if card plans already exist
            if self.card_plan_ids:
                raise UserError(_("Card plans already exist for this journal."))
            
            # Create basic card plans
            default_plans = [
                {
                    'name': f'Debit Card - {self.name}',
                    'days_to_accreditation': 1,
                    'commission_percentage': 2.5,
                    'financial_cost': 0.0,
                    'surcharge_coefficient': 1.03,
                    'journal_id': self.id,
                },
                {
                    'name': f'Credit Card - {self.name}',
                    'days_to_accreditation': 18,
                    'commission_percentage': 3.5,
                    'financial_cost': 1.5,
                    'surcharge_coefficient': 1.05,
                    'journal_id': self.id,
                }
            ]
            
            for plan_data in default_plans:
                self.env['card.plan'].create(plan_data)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('Default card plans created successfully.'),
                    'type': 'success',
                }
            }
            
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': str(e),
                    'type': 'danger',
                }
            }

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to setup card-related configurations"""
        journals = super(AccountJournal, self).create(vals_list)
        
        for journal in journals:
            if journal.is_credit_card:
                journal.create_default_reconcile_models()
                journal.create_default_card_plans()
        
        return journals

    def write(self, vals):
        """Override write to setup card-related configurations"""
        result = super(AccountJournal, self).write(vals)
        
        if vals.get('is_credit_card'):
            for journal in self:
                journal.create_default_reconcile_models()
                journal.create_default_card_plans()
        
        return result

    def action_configure_payment_accounts(self):
        """Configure payment accounts for credit card payment method lines"""
        self.ensure_one()
        
        if not self.is_credit_card:
            raise UserError("This action is only available for credit card journals.")
        
        # Get or create a suitable payment account
        payment_account = self.default_account_id
        if not payment_account:
            # Create a default payment account if none exists
            account_vals = {
                'name': f'{self.name} - Payment Account',
                'code': f'101001{self.id}',  # Simple numbering scheme
                'account_type': 'asset_current',
                'company_id': self.company_id.id,
            }
            payment_account = self.env['account.account'].create(account_vals)
            self.default_account_id = payment_account.id
        
        # Configure payment accounts for all payment method lines
        all_lines = self.inbound_payment_method_line_ids + self.outbound_payment_method_line_ids
        for line in all_lines:
            if not line.payment_account_id:
                line.payment_account_id = payment_account.id
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': f'Payment accounts configured for {self.name}',
                'type': 'success',
            }
        }