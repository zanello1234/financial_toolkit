from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

# Track clicks on reconcile model buttons specifically
_logger.warning("=== BankRecWidget loaded - TRACKING MODEL BUTTON CLICKS ===")


class BankRecWidget(models.Model):
    _inherit = 'bank.rec.widget'
    
    def onchange(self, vals, field_name, field_onchange):
        """Track onchange calls and intercept select_reconcile_model"""
        if 'todo_command' in vals:
            command = vals.get('todo_command', {})
            method_name = command.get('method_name', '')
            
            # Track ALL commands to find the correct one for model application
            _logger.warning(f"=== COMMAND: {method_name} - ARGS: {command.get('args', [])} ===")
            
            # INTERCEPT select_reconcile_model for our custom types
            if method_name == 'select_reconcile_model':
                model_id = command.get('args', [None])[0] if command.get('args') else None
                _logger.warning(f"*** MODEL SELECTED: {model_id} ***")
                
                if model_id:
                    try:
                        reconcile_model = self.env['account.reconcile.model'].browse(model_id)
                        if reconcile_model.exists() and reconcile_model.counterpart_type in ['customer_receipts', 'vendor_payments']:
                            _logger.warning(f"*** CUSTOM MODEL DETECTED: {reconcile_model.counterpart_type} ***")
                            _logger.warning(f"*** MODEL NAME: {reconcile_model.name} ***")
                            
                            # Get statement line from vals
                            st_line_id = vals.get('st_line_id')
                            if st_line_id:
                                st_line = self.env['account.bank.statement.line'].browse(st_line_id)
                                if st_line.exists():
                                    _logger.warning(f"*** CREATING PAYMENT FOR: {st_line.payment_ref} - Amount: {st_line.amount} ***")
                                    
                                    # Create payment INSTEAD of just selecting the model
                                    result = reconcile_model._create_payment_from_reconcile_model(st_line)
                                    _logger.warning(f"*** PAYMENT CREATION RESULT: {result} ***")
                                    
                                    if result and 'payment_id' in result:
                                        _logger.warning(f"*** SUCCESS: Payment {result['payment_id']} created! ***")
                                        
                                        # Call super to let normal flow continue with payment available
                                        # This should make the payment appear in the reconciliation options
                                        pass
                                    
                    except Exception as e:
                        _logger.error(f"Error creating payment on model select: {e}")
                        import traceback
                        _logger.error(f"Traceback: {traceback.format_exc()}")
            
            elif method_name == 'validate':
                _logger.warning("*** VALIDATE (should only reconcile, not create payments) ***")
            
        # Always call super() to maintain normal flow
        return super().onchange(vals, field_name, field_onchange)