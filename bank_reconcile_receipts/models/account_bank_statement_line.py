from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    def button_reconcile(self):
        """Track reconcile button on statement line"""
        _logger.warning(f"=== BankStatementLine button_reconcile called ===")
        _logger.warning(f"Statement line: {self.payment_ref} - Amount: {self.amount}")
        return super().button_reconcile()

    def action_reconcile(self):
        """Track reconcile action on statement line"""
        _logger.warning(f"=== BankStatementLine action_reconcile called ===")
        _logger.warning(f"Statement line: {self.payment_ref} - Amount: {self.amount}")
        return super().action_reconcile()

    def reconcile(self, reconcile_model_id=None):
        """Track reconcile method with model"""
        _logger.warning(f"=== BankStatementLine reconcile called ===")
        _logger.warning(f"Statement line: {self.payment_ref} - Amount: {self.amount}")
        if reconcile_model_id:
            reconcile_model = self.env['account.reconcile.model'].browse(reconcile_model_id)
            _logger.warning(f"Using reconcile model: {reconcile_model.name} - Type: {reconcile_model.counterpart_type}")
            if reconcile_model.counterpart_type == 'invoice':
                _logger.warning("INVOICE RECONCILIATION DETECTED IN STATEMENT LINE")
        if hasattr(super(), 'reconcile'):
            return super().reconcile(reconcile_model_id)
        else:
            return {}

    def apply_reconcile_model(self, reconcile_model_id):
        """Track apply reconcile model on statement line"""
        _logger.warning(f"=== BankStatementLine apply_reconcile_model called ===")
        _logger.warning(f"Statement line: {self.payment_ref} - Amount: {self.amount}")
        reconcile_model = self.env['account.reconcile.model'].browse(reconcile_model_id)
        _logger.warning(f"Applying model: {reconcile_model.name} - Type: {reconcile_model.counterpart_type}")
        if reconcile_model.counterpart_type == 'invoice':
            _logger.warning("INVOICE MODEL BEING APPLIED TO STATEMENT LINE")
        if hasattr(super(), 'apply_reconcile_model'):
            return super().apply_reconcile_model(reconcile_model_id)
        else:
            return {}