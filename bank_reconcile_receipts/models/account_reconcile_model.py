from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class AccountReconcileModel(models.Model):
    _inherit = 'account.reconcile.model'

    # Extender las opciones de counterpart_type
    counterpart_type = fields.Selection(
        selection_add=[
            ('customer_receipts', 'Customer Receipts'),
            ('vendor_payments', 'Vendor Payments'),
        ],
        ondelete={
            'customer_receipts': 'cascade',
            'vendor_payments': 'cascade',
        }
    )

    # Campos adicionales para configurar los pagos/recibos
    payment_method_line_id = fields.Many2one(
        'account.payment.method.line',
        string='Payment Method',
        help="Payment method to use when creating receipts or payments"
    )
    
    auto_post_payment = fields.Boolean(
        string='Auto-post Payment',
        default=True,
        help="Automatically post the created payment/receipt"
    )
    
    payment_memo_template = fields.Char(
        string='Payment Memo Template',
        default='Bank reconciliation: {statement_name}',
        help="Template for payment memo. Available variables: {statement_name}, {partner_name}, {amount}"
    )

    def _apply_reconcile_model(self, st_line, partner_map=None):
        """Override to handle payment creation for custom counterpart types"""
        _logger.warning(f"=== _apply_reconcile_model called ===")
        _logger.warning(f"Reconcile model: {self.name} - counterpart_type: {self.counterpart_type}")
        _logger.warning(f"Statement line: {st_line.payment_ref} - Amount: {st_line.amount}")
        _logger.warning(f"Method being called: _apply_reconcile_model")
        
        try:
            if self.counterpart_type in ['customer_receipts', 'vendor_payments']:
                _logger.warning(f"*** INTERCEPTING: Creating payment for {self.counterpart_type} instead of standard reconciliation ***")
                result = self._create_payment_from_reconcile_model(st_line)
                _logger.warning(f"Payment creation result: {result}")
                _logger.warning(f"Result type: {type(result)}")
                if hasattr(result, 'get') and result.get('payment_id'):
                    _logger.warning(f"*** SUCCESS: Payment ID created: {result['payment_id']} ***")
                return result
            else:
                _logger.warning(f"Using standard reconciliation for counterpart_type: {self.counterpart_type}")
                if self.counterpart_type == 'invoice':
                    _logger.warning("INVOICE TYPE - THIS IS THE FLOW WE WANT TO REPLICATE FOR PAYMENTS")
                return super()._apply_reconcile_model(st_line, partner_map)
        except Exception as e:
            _logger.error(f"*** ERROR in _apply_reconcile_model: {e} ***")
            import traceback
            _logger.error(f"Traceback: {traceback.format_exc()}")
            # Fall back to standard flow on error
            return super()._apply_reconcile_model(st_line, partner_map)

    def test_payment_creation(self, st_line_id):
        """Test method to verify payment creation works"""
        _logger.warning(f"=== test_payment_creation called ===")
        _logger.warning(f"Model: {self.name} - Type: {self.counterpart_type}")
        
        if self.counterpart_type in ['customer_receipts', 'vendor_payments']:
            st_line = self.env['account.bank.statement.line'].browse(st_line_id)
            if st_line.exists():
                _logger.warning(f"*** TESTING PAYMENT CREATION FOR: {st_line.payment_ref} ***")
                result = self._create_payment_from_reconcile_model(st_line)
                _logger.warning(f"*** TEST RESULT: {result} ***")
                return result
        return False
    
    # Add more tracking methods
    def action_apply_reconcile_model(self, statement_line_id=None):
        """Track when reconcile model is applied via action"""
        _logger.warning(f"=== action_apply_reconcile_model called ===")
        _logger.warning(f"Model: {self.name} - Type: {self.counterpart_type}")
        if statement_line_id:
            _logger.warning(f"Statement line ID: {statement_line_id}")
        if hasattr(super(), 'action_apply_reconcile_model'):
            return super().action_apply_reconcile_model(statement_line_id)
        else:
            return {}
    
    def apply_reconcile_model(self, statement_line_id=None):
        """Track when reconcile model is applied"""
        _logger.warning(f"=== apply_reconcile_model called ===")
        _logger.warning(f"Model: {self.name} - Type: {self.counterpart_type}")
        if hasattr(super(), 'apply_reconcile_model'):
            return super().apply_reconcile_model(statement_line_id)
        else:
            return {}

    def action_reconcile_bank_line(self, bank_line_id):
        """Override button action to handle payment creation"""
        _logger.warning(f"=== action_reconcile_bank_line called ===")
        _logger.warning(f"Model: {self.name} - Type: {self.counterpart_type}")
        _logger.warning(f"Bank line ID: {bank_line_id}")
        _logger.warning(f"Method being called: action_reconcile_bank_line")
        
        try:
            if self.counterpart_type in ['customer_receipts', 'vendor_payments']:
                _logger.warning(f"*** INTERCEPTING BUTTON: Creating payment from button action for {self.counterpart_type} ***")
                bank_line = self.env['account.bank.statement.line'].browse(bank_line_id)
                _logger.warning(f"Bank line: {bank_line.payment_ref} - Amount: {bank_line.amount}")
                result = self._create_payment_from_reconcile_model(bank_line)
                _logger.warning(f"*** BUTTON RESULT: Payment creation result: {result} ***")
                return result
            else:
                if self.counterpart_type == 'invoice':
                    _logger.warning("INVOICE BUTTON ACTION - THIS IS THE FLOW WE WANT TO REPLICATE")
                _logger.warning("Using standard button action")
                return super().action_reconcile_bank_line(bank_line_id)
        except Exception as e:
            _logger.error(f"*** ERROR in action_reconcile_bank_line: {e} ***")
            import traceback
            _logger.error(f"Traceback: {traceback.format_exc()}")
            # Fall back to standard flow on error
            return super().action_reconcile_bank_line(bank_line_id)

    @api.model
    def _get_invoice_matching_query(self, st_lines, partner_map, reconciled_amls):
        """Override to handle our custom counterpart types"""
        # For our custom types, we don't want invoice matching
        custom_types = ['customer_receipts', 'vendor_payments']
        if any(line.reconcile_model_id.counterpart_type in custom_types for line in st_lines):
            return super()._get_invoice_matching_query(st_lines, partner_map, reconciled_amls)
        return super()._get_invoice_matching_query(st_lines, partner_map, reconciled_amls)

    def _get_write_off_move_lines_dict(self, st_line, move_lines=None):
        """Override to create payments instead of write-off entries for custom counterpart types"""
        _logger.info(f"=== _get_write_off_move_lines_dict called ===")
        _logger.info(f"Reconcile model: {self.name} - counterpart_type: {self.counterpart_type}")
        _logger.info(f"Statement line: {st_line.payment_ref} - Amount: {st_line.amount}")
        
        if self.counterpart_type in ['customer_receipts', 'vendor_payments']:
            _logger.info(f"Creating payment for {self.counterpart_type} instead of write-off")
            result = self._create_payment_from_reconcile_model(st_line)
            _logger.info(f"Payment creation result: {result}")
            # Return empty dict to prevent standard write-off creation
            return {}
        else:
            _logger.info(f"Using standard write-off for counterpart_type: {self.counterpart_type}")
            return super()._get_write_off_move_lines_dict(st_line, move_lines)

    def _create_payment_from_reconcile_model(self, st_line):
        """Create payment/receipt based on reconcile model configuration"""
        _logger.info(f"*** PAYMENT CREATION STARTED ***")
        _logger.info(f"Creating payment for statement line: {st_line.payment_ref} - Amount: {st_line.amount}")
        _logger.info(f"Reconcile model: {self.name} - Type: {self.counterpart_type}")
        
        # Use self as the reconcile model since this method is called on the model instance
        reconcile_model = self
        counterpart_type = reconcile_model.counterpart_type
        
        _logger.info(f"Counterpart type: {counterpart_type}")
        
        # Determinar tipo de pago y partner
        if counterpart_type == 'customer_receipts':
            payment_type = 'inbound'
            partner_type = 'customer'
            _logger.info("Creating CUSTOMER RECEIPT (inbound payment)")
        elif counterpart_type == 'vendor_payments':
            payment_type = 'outbound'
            partner_type = 'supplier'
            _logger.info("Creating VENDOR PAYMENT (outbound payment)")
        else:
            _logger.error(f"Unsupported counterpart type: {counterpart_type}")
            return {'moves': self.env['account.move']}
        
        # Obtener partner de la línea de extracto
        partner_id = st_line.partner_id
        _logger.info(f"Statement line partner: {partner_id.name if partner_id else 'None'}")
        
        if not partner_id:
            # Buscar partner por nombre si no está asignado
            if st_line.payment_ref:
                _logger.info(f"Searching partner by payment reference: {st_line.payment_ref}")
                partner_domain = [
                    ('is_company', '=', True),
                    ('name', 'ilike', st_line.payment_ref[:50])
                ]
                if partner_type == 'customer':
                    partner_domain.append(('customer_rank', '>', 0))
                else:
                    partner_domain.append(('supplier_rank', '>', 0))
                
                partner_id = self.env['res.partner'].search(partner_domain, limit=1)
                
        if not partner_id:
            _logger.warning(f"No partner found for statement line {st_line.id}")
            return {'moves': self.env['account.move']}
        
        # Preparar memo del pago
        memo = reconcile_model.payment_memo_template or 'Bank reconciliation payment'
        memo = memo.format(
            statement_name=st_line.statement_id.name or '',
            partner_name=partner_id.name or '',
            amount=st_line.amount
        )
        
        # Obtener método de pago
        payment_method_line = reconcile_model.payment_method_line_id
        if not payment_method_line:
            # Buscar método de pago por defecto en el journal de la línea de extracto
            journal = st_line.journal_id
            available_methods = journal._get_available_payment_method_lines(payment_type)
            payment_method_line = available_methods[:1] if available_methods else False
            
        if not payment_method_line:
            # Si aún no tenemos método de pago, buscar uno genérico
            payment_method_lines = self.env['account.payment.method.line'].search([
                ('payment_type', '=', payment_type),
                ('company_id', '=', st_line.company_id.id)
            ], limit=1)
            payment_method_line = payment_method_lines[:1] if payment_method_lines else False
            
        if not payment_method_line:
            _logger.error(f"No payment method found for payment type {payment_type}")
            return {'moves': self.env['account.move']}
        
        # Crear el pago
        payment_vals = {
            'payment_type': payment_type,
            'partner_type': partner_type,
            'partner_id': partner_id.id,
            'amount': abs(st_line.amount),
            'currency_id': st_line.currency_id.id or st_line.journal_id.currency_id.id or self.env.company.currency_id.id,
            'journal_id': st_line.journal_id.id,
            'payment_method_line_id': payment_method_line.id,
            'date': st_line.date,
            'memo': memo,
            # 'ref': st_line.payment_ref or st_line.ref,  # REMOVED - field doesn't exist in account.payment
        }
        
        _logger.info(f"Creating payment with values: {payment_vals}")
        
        try:
            payment = self.env['account.payment'].create(payment_vals)
            _logger.info(f"Payment created with ID: {payment.id} - Name: {payment.name}")
            
            # Auto-post el payment para que genere las líneas contables
            if reconcile_model.auto_post_payment:
                payment.action_post()
                _logger.info(f"Payment {payment.id} posted automatically")
                
                # Buscar la línea contable del payment que coincide con la cuenta del banco
                bank_account = st_line.journal_id.default_account_id
                payment_line = payment.move_id.line_ids.filtered(
                    lambda line: line.account_id == bank_account and line.balance != 0
                )
                
                if payment_line:
                    _logger.info(f"Found payment line: {payment_line.id} - Account: {payment_line.account_id.name} - Balance: {payment_line.balance}")
                    
                    # En lugar de marcar manualmente, vamos a retornar las líneas que deben reconciliarse
                    # Esto permite que el sistema maneje la reconciliación automáticamente
                    _logger.info(f"Returning payment move {payment.move_id.id} for reconciliation")
                    
                    # Retornar el move del payment para que se procese en la reconciliación bancaria
                    return {
                        'moves': payment.move_id,
                        'payment_id': payment.id,
                    }
                else:
                    _logger.warning(f"No payment line found for account {bank_account.name}")
            else:
                _logger.info(f"Payment {payment.id} created but not posted (auto_post_payment=False)")
                
            # Si no se pudo reconciliar automáticamente, al menos retornar el move
            return {
                'moves': payment.move_id,
                'payment_id': payment.id,
            }
                
        except Exception as e:
            _logger.error(f"Error creating payment: {str(e)}")
            import traceback
            _logger.error(f"Traceback: {traceback.format_exc()}")
            # Retornar un resultado vacío en caso de error
            return {'moves': self.env['account.move']}

    def get_payment_info(self, payment_id):
        """Helper method to get payment information"""
        payment = self.env['account.payment'].browse(payment_id)
        if payment.exists():
            _logger.info(f"Payment Info - ID: {payment.id}, Name: {payment.name}, State: {payment.state}")
            _logger.info(f"Payment Info - Partner: {payment.partner_id.name}, Amount: {payment.amount}")
            _logger.info(f"Payment Info - Journal: {payment.journal_id.name}, Move: {payment.move_id.name if payment.move_id else 'No Move'}")
            return {
                'id': payment.id,
                'name': payment.name,
                'state': payment.state,
                'partner': payment.partner_id.name,
                'amount': payment.amount,
                'journal': payment.journal_id.name,
                'move_name': payment.move_id.name if payment.move_id else None,
            }
        return None

    def _reconcile_payment_with_statement_line(self, payment, st_line):
        """Reconcile the created payment with the bank statement line"""
        try:
            # Buscar las líneas contables del pago que coincidan con la cuenta del journal
            payment_lines = payment.move_id.line_ids.filtered(
                lambda l: l.account_id == st_line.journal_id.default_account_id and not l.reconciled
            )
            
            if payment_lines:
                # Crear la reconciliación
                lines_to_reconcile = payment_lines
                
                # Si la statement line ya tiene move_id, incluir esas líneas también
                if st_line.move_id:
                    statement_lines = st_line.move_id.line_ids.filtered(
                        lambda l: l.account_id == st_line.journal_id.default_account_id and not l.reconciled
                    )
                    lines_to_reconcile |= statement_lines
                
                if len(lines_to_reconcile) > 1:
                    lines_to_reconcile.reconcile()
                    _logger.info(f"Payment {payment.id} reconciled with statement line {st_line.id}")
                    
        except Exception as e:
            _logger.error(f"Error reconciling payment with statement line: {str(e)}")

    @api.onchange('counterpart_type')
    def _onchange_counterpart_type(self):
        """Reset payment-specific fields when counterpart type changes"""
        if self.counterpart_type not in ['customer_receipts', 'vendor_payments']:
            self.payment_method_line_id = False
            self.auto_post_payment = True
            self.payment_memo_template = 'Bank reconciliation: {statement_name}'

    @api.constrains('counterpart_type', 'payment_method_line_id')
    def _check_payment_method_compatibility(self):
        """Ensure payment method is compatible with the counterpart type"""
        for record in self:
            if record.counterpart_type in ['customer_receipts', 'vendor_payments']:
                if record.payment_method_line_id:
                    expected_type = 'inbound' if record.counterpart_type == 'customer_receipts' else 'outbound'
                    if record.payment_method_line_id.payment_type != expected_type:
                        raise ValidationError(_(
                            'Payment method type (%s) does not match counterpart type (%s)'
                        ) % (record.payment_method_line_id.payment_type, record.counterpart_type))

    @api.onchange('counterpart_type')
    def _onchange_counterpart_type_payment_method(self):
        """Clear payment method when counterpart type changes"""
        if self.counterpart_type not in ['customer_receipts', 'vendor_payments']:
            self.payment_method_line_id = False