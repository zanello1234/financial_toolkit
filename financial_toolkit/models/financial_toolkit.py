from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class FinancialToolkit(models.TransientModel):
    """
    Financial Toolkit configuration and status model
    """
    _name = 'financial.toolkit'
    _description = 'Financial Toolkit Configuration'

    name = fields.Char(string='Name', default='Financial Toolkit')
    
    # Status fields for each module
    bank_reconcile_receipts_installed = fields.Boolean(
        string='Bank Reconciliation Receipts',
        compute='_compute_module_status',
        help="Create customer receipts and vendor payments from bank reconciliation"
    )
    
    credit_card_journal_installed = fields.Boolean(
        string='Credit Card Journal',
        compute='_compute_module_status',
        help="Enhanced credit card statement processing and workflows"
    )
    
    journal_partner_restriction_installed = fields.Boolean(
        string='Journal Partner Restrictions',
        compute='_compute_module_status',
        help="Control which partners can use specific journals"
    )
    
    liquidity_journal_actions_installed = fields.Boolean(
        string='Liquidity Journal Actions',
        compute='_compute_module_status',
        help="Advanced liquidity management and bank journal operations"
    )
    
    account_internal_transfer_installed = fields.Boolean(
        string='Account Internal Transfers',
        compute='_compute_module_status',
        help="Internal transfer management between accounts"
    )

    @api.depends()
    def _compute_module_status(self):
        """Compute installation status of each financial module"""
        modules_to_check = [
            'bank_reconcile_receipts',
            'credit_card_journal',
            'journal_partner_restriction', 
            'liquidity_journal_actions',
            'account_internal_transfer',
        ]
        
        for record in self:
            for module_name in modules_to_check:
                module = self.env['ir.module.module'].search([
                    ('name', '=', module_name)
                ], limit=1)
                
                field_name = f"{module_name}_installed"
                is_installed = module and module.state == 'installed'
                setattr(record, field_name, is_installed)

    def action_install_missing_modules(self):
        """Install any missing financial modules"""
        _logger.info("=== Installing missing financial modules ===")
        
        modules_to_install = [
            'bank_reconcile_receipts',
            'credit_card_journal',
            'journal_partner_restriction', 
            'liquidity_journal_actions',
            'account_internal_transfer',
        ]
        
        installed_count = 0
        
        for module_name in modules_to_install:
            module = self.env['ir.module.module'].search([
                ('name', '=', module_name)
            ], limit=1)
            
            if module and module.state not in ['installed', 'to upgrade']:
                _logger.info(f"Installing module: {module_name}")
                module.button_immediate_install()
                installed_count += 1
            elif module and module.state == 'installed':
                _logger.info(f"Module already installed: {module_name}")
            else:
                _logger.warning(f"Module not found: {module_name}")
        
        # Refresh the view
        self._compute_module_status()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Financial Toolkit: {installed_count} modules installed successfully!',
                'type': 'success',
            }
        }

    def action_open_bank_reconciliation(self):
        """Open enhanced bank reconciliation"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bank Reconciliation',
            'res_model': 'account.bank.statement.line',
            'view_mode': 'list,form',
            'domain': [('is_reconciled', '=', False)],
            'context': {'search_default_unreconciled': 1},
        }

    def action_open_reconcile_models(self):
        """Open reconciliation models configuration"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reconciliation Models',
            'res_model': 'account.reconcile.model',
            'view_mode': 'list,form',
        }

    def action_open_journal_config(self):
        """Open journal configuration"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Journal Configuration',
            'res_model': 'account.journal',
            'view_mode': 'list,form',
        }

    def action_open_payments(self):
        """Open payments view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payments',
            'res_model': 'account.payment',
            'view_mode': 'list,form',
        }