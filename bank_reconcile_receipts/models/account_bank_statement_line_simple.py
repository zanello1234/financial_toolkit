from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    def action_create_payment_receipt(self):
        """Simple button action to create payment/receipt directly"""
        _logger.warning(f"=== DIRECT PAYMENT CREATION STARTED ===")
        _logger.warning(f"Number of lines to process: {len(self)}")
        
        created_payments = []
        skipped_lines = []
        
        for line in self:
            _logger.warning(f"Processing line {line.id}: {line.payment_ref} - Amount: {line.amount}")
            _logger.warning(f"Line reconciled status: {line.is_reconciled}")
            
            if line.is_reconciled:
                _logger.warning(f"Line {line.id} already reconciled, skipping")
                skipped_lines.append(line)
                continue
                
            # Determine payment type based on amount
            if line.amount > 0:
                payment_type = 'inbound'
                partner_type = 'customer'
                action_name = "Customer Receipt"
            else:
                payment_type = 'outbound' 
                partner_type = 'supplier'
                action_name = "Vendor Payment"
            
            _logger.warning(f"Creating {action_name} for line {line.id} - Amount: {line.amount}")
            
            # Get or create partner
            partner_id = line.partner_id
            _logger.warning(f"Initial partner: {partner_id.name if partner_id else 'None'}")
            
            if not partner_id and line.payment_ref:
                # Try to find partner by name
                _logger.warning(f"Searching partner by payment_ref: {line.payment_ref}")
                partner_id = self.env['res.partner'].search([
                    ('name', 'ilike', line.payment_ref[:50])
                ], limit=1)
                _logger.warning(f"Found partner by search: {partner_id.name if partner_id else 'None'}")
            
            if not partner_id:
                # Create a generic partner if none found
                partner_name = line.payment_ref or f"Bank Transaction {line.date}"
                _logger.warning(f"Creating new partner: {partner_name}")
                partner_id = self.env['res.partner'].create({
                    'name': partner_name,
                    'is_company': True,
                    'customer_rank': 1 if payment_type == 'inbound' else 0,
                    'supplier_rank': 1 if payment_type == 'outbound' else 0,
                })
                _logger.warning(f"Created new partner: {partner_id.name} (ID: {partner_id.id})")
            
            # Get payment method
            _logger.warning(f"Getting payment methods for type: {payment_type} in journal: {line.journal_id.name}")
            available_methods = line.journal_id._get_available_payment_method_lines(payment_type)
            _logger.warning(f"Available methods: {[m.name for m in available_methods]}")
            payment_method_line = available_methods[:1] if available_methods else False
            
            if not payment_method_line:
                error_msg = f"No payment method available for {payment_type} payments in journal {line.journal_id.name}"
                _logger.error(error_msg)
                raise UserError(error_msg)
            
            _logger.warning(f"Using payment method: {payment_method_line.name}")
            
            # Create payment
            payment_vals = {
                'payment_type': payment_type,
                'partner_type': partner_type,
                'partner_id': partner_id.id,
                'amount': abs(line.amount),
                'currency_id': line.currency_id.id or line.journal_id.currency_id.id or self.env.company.currency_id.id,
                'journal_id': line.journal_id.id,
                'payment_method_line_id': payment_method_line.id,
                'date': line.date,
                'memo': f"Bank reconciliation: {line.payment_ref or line.ref}",
                # 'ref': line.payment_ref or line.ref,  # REMOVED - field doesn't exist in account.payment
            }
            
            _logger.warning(f"Payment values: {payment_vals}")
            
            try:
                _logger.warning("Creating payment record...")
                payment = self.env['account.payment'].create(payment_vals)
                _logger.warning(f"Payment created with ID: {payment.id}")
                
                _logger.warning("Posting payment...")
                payment.action_post()
                _logger.warning(f"Payment {payment.name} posted successfully")
                
                # Mark the line as reconciled
                _logger.warning("Marking statement line as reconciled...")
                line.write({
                    'is_reconciled': True,
                    'move_id': payment.move_id.id
                })
                _logger.warning(f"Line {line.id} marked as reconciled with move {payment.move_id.id}")
                
                created_payments.append(payment)
                
            except Exception as e:
                _logger.error(f"Error creating payment for line {line.id}: {str(e)}")
                import traceback
                _logger.error(f"Traceback: {traceback.format_exc()}")
                raise UserError(f"Error creating payment for line {line.id}: {str(e)}")
        
        _logger.warning(f"=== PAYMENT CREATION COMPLETED ===")
        _logger.warning(f"Created {len(created_payments)} payments")
        _logger.warning(f"Skipped {len(skipped_lines)} already reconciled lines")
        
        if created_payments:
            if len(created_payments) == 1:
                # Show single payment
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Created Payment',
                    'res_model': 'account.payment',
                    'res_id': created_payments[0].id,
                    'view_mode': 'form',
                    'target': 'current',
                }
            else:
                # Show list of created payments
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Created Payments',
                    'res_model': 'account.payment',
                    'domain': [('id', 'in', [p.id for p in created_payments])],
                    'view_mode': 'list,form',
                    'target': 'current',
                }
        elif skipped_lines:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'All {len(skipped_lines)} selected lines are already reconciled. Please select unreconciled lines.',
                    'type': 'warning',
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No payments were created. Check logs for details.',
                    'type': 'warning',
                }
            }

    def action_force_create_payment_receipt(self):
        """Force create payment/receipt even for reconciled lines - FOR TESTING"""
        _logger.warning(f"=== FORCE PAYMENT CREATION STARTED ===")
        _logger.warning(f"Number of lines to process: {len(self)}")
        
        created_payments = []
        
        for line in self:
            _logger.warning(f"Force processing line {line.id}: {line.payment_ref} - Amount: {line.amount}")
            _logger.warning(f"Line reconciled status: {line.is_reconciled} (ignoring for testing)")
                
            # Determine payment type based on amount
            if line.amount > 0:
                payment_type = 'inbound'
                partner_type = 'customer'
                action_name = "Customer Receipt"
            else:
                payment_type = 'outbound' 
                partner_type = 'supplier'
                action_name = "Vendor Payment"
            
            _logger.warning(f"Creating {action_name} for line {line.id} - Amount: {line.amount}")
            
            # Get or create partner
            partner_id = line.partner_id
            _logger.warning(f"Initial partner: {partner_id.name if partner_id else 'None'}")
            
            if not partner_id and line.payment_ref:
                # Try to find partner by name
                _logger.warning(f"Searching partner by payment_ref: {line.payment_ref}")
                partner_id = self.env['res.partner'].search([
                    ('name', 'ilike', line.payment_ref[:50])
                ], limit=1)
                _logger.warning(f"Found partner by search: {partner_id.name if partner_id else 'None'}")
            
            if not partner_id:
                # Create a generic partner if none found
                partner_name = line.payment_ref or f"Bank Transaction {line.date}"
                _logger.warning(f"Creating new partner: {partner_name}")
                partner_id = self.env['res.partner'].create({
                    'name': partner_name,
                    'is_company': True,
                    'customer_rank': 1 if payment_type == 'inbound' else 0,
                    'supplier_rank': 1 if payment_type == 'outbound' else 0,
                })
                _logger.warning(f"Created new partner: {partner_id.name} (ID: {partner_id.id})")
            
            # Get payment method
            _logger.warning(f"Getting payment methods for type: {payment_type} in journal: {line.journal_id.name}")
            available_methods = line.journal_id._get_available_payment_method_lines(payment_type)
            _logger.warning(f"Available methods: {[m.name for m in available_methods]}")
            payment_method_line = available_methods[:1] if available_methods else False
            
            if not payment_method_line:
                error_msg = f"No payment method available for {payment_type} payments in journal {line.journal_id.name}"
                _logger.error(error_msg)
                raise UserError(error_msg)
            
            _logger.warning(f"Using payment method: {payment_method_line.name}")
            
            # Create payment
            payment_vals = {
                'payment_type': payment_type,
                'partner_type': partner_type,
                'partner_id': partner_id.id,
                'amount': abs(line.amount),
                'currency_id': line.currency_id.id or line.journal_id.currency_id.id or self.env.company.currency_id.id,
                'journal_id': line.journal_id.id,
                'payment_method_line_id': payment_method_line.id,
                'date': line.date,
                'memo': f"Bank reconciliation (TESTING): {line.payment_ref or line.ref}",
                # 'ref': line.payment_ref or line.ref,  # REMOVED - field doesn't exist in account.payment
            }
            
            _logger.warning(f"Payment values: {payment_vals}")
            
            try:
                _logger.warning("Creating payment record...")
                payment = self.env['account.payment'].create(payment_vals)
                _logger.warning(f"Payment created with ID: {payment.id}")
                
                _logger.warning("Posting payment...")
                payment.action_post()
                _logger.warning(f"Payment {payment.name} posted successfully")
                
                created_payments.append(payment)
                
            except Exception as e:
                _logger.error(f"Error creating payment for line {line.id}: {str(e)}")
                import traceback
                _logger.error(f"Traceback: {traceback.format_exc()}")
                raise UserError(f"Error creating payment for line {line.id}: {str(e)}")
        
        _logger.warning(f"=== FORCE PAYMENT CREATION COMPLETED ===")
        _logger.warning(f"Created {len(created_payments)} payments")
        
        if created_payments:
            if len(created_payments) == 1:
                # Show single payment
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Created Payment (TESTING)',
                    'res_model': 'account.payment',
                    'res_id': created_payments[0].id,
                    'view_mode': 'form',
                    'target': 'current',
                }
            else:
                # Show list of created payments
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Created Payments (TESTING)',
                    'res_model': 'account.payment',
                    'domain': [('id', 'in', [p.id for p in created_payments])],
                    'view_mode': 'list,form',
                    'target': 'current',
                }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'No payments were created. Check logs for details.',
                    'type': 'warning',
                }
            }