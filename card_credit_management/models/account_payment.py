# © 2025 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    card_plan_id = fields.Many2one(
        'card.plan',
        string='Credit Card Plan',
        help='Credit card plan for this payment'
    )
    
    card_batch_number = fields.Char(
        string='Batch Number',
        help='Credit card batch number (e.g., Lote 047, Lote 055)'
    )
    
    card_coupon_number = fields.Char(
        string='Coupon Number',
        help='Credit card coupon number'
    )
    
    # is_card_payment = fields.Boolean(
    #     string='Is Card Payment',
    #     default=False,
    #     help='Indicates if this payment is related to credit card accreditation'
    # )
    
    estimated_accreditation_date = fields.Date(
        string='Estimated Accreditation Date',
        compute='_compute_estimated_accreditation_date',
        store=True,
        help='Estimated date when the payment will be credited'
    )
    
    estimated_liquidation_amount = fields.Monetary(
        string='Estimated Liquidation Amount',
        compute='_compute_estimated_liquidation_amount',
        store=True,
        help='Estimated amount to be liquidated after fees and financial costs'
    )
    
    # Calculation breakdown fields
    estimated_fee_amount = fields.Monetary(
        string='Estimated Fee Amount',
        compute='_compute_estimated_amounts',
        store=True,
        help='Estimated fee amount based on card plan'
    )
    
    estimated_financial_cost_amount = fields.Monetary(
        string='Estimated Financial Cost',
        compute='_compute_estimated_amounts',
        store=True,
        help='Estimated financial cost based on card plan'
    )
    
    card_plan_fee_percentage = fields.Float(
        string='Fee Percentage',
        related='card_plan_id.fee_percentage',
        readonly=True,
        help='Fee percentage from card plan'
    )
    
    card_plan_financial_cost_percentage = fields.Float(
        string='Financial Cost Percentage',
        related='card_plan_id.financial_cost_percentage',
        readonly=True,
        help='Financial cost percentage from card plan'
    )
    
    # Internal Transfer fields following account_internal_transfer pattern
    paired_internal_transfer_payment_id = fields.Many2one(
        'account.payment',
        string='Paired Internal Transfer Payment',
        help='The paired payment for internal transfers'
    )
    
    is_internal_transfer = fields.Boolean(
        string='Is Internal Transfer',
        default=False,
        help='Indicates if this payment is part of an internal transfer'
    )
    
    destination_journal_id = fields.Many2one(
        'account.journal',
        string='Destination Journal',
        help='Destination journal for internal transfers'
    )

    @api.depends('card_plan_id', 'date')
    def _compute_estimated_accreditation_date(self):
        for payment in self:
            if payment.card_plan_id and payment.date:
                payment.estimated_accreditation_date = payment.card_plan_id.calculate_accreditation_date(payment.date)
            else:
                payment.estimated_accreditation_date = False

    @api.depends('card_plan_id', 'amount')
    def _compute_estimated_liquidation_amount(self):
        for payment in self:
            if payment.card_plan_id and payment.amount:
                payment.estimated_liquidation_amount = payment.card_plan_id.calculate_estimated_amount(payment.amount)
            else:
                payment.estimated_liquidation_amount = 0

    @api.depends('card_plan_id', 'amount')
    def _compute_estimated_amounts(self):
        """Calculate estimated fee and financial cost amounts"""
        for payment in self:
            if payment.card_plan_id and payment.amount:
                # Calculate fee amount
                fee_percentage = payment.card_plan_id.fee_percentage or 0
                payment.estimated_fee_amount = payment.amount * (fee_percentage / 100)
                
                # Calculate financial cost amount
                financial_cost_percentage = payment.card_plan_id.financial_cost_percentage or 0
                payment.estimated_financial_cost_amount = payment.amount * (financial_cost_percentage / 100)
            else:
                payment.estimated_fee_amount = 0
                payment.estimated_financial_cost_amount = 0

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        """Limpiar campos de tarjeta cuando cambia el diario"""
        # Skip clearing fields for internal transfers
        if self.is_internal_transfer:
            return
            
        if not self.journal_id or not self.journal_id.is_credit_card:
            self.card_plan_id = False
            self.card_batch_number = False
            self.card_coupon_number = False

    @api.constrains('journal_id', 'card_plan_id', 'card_batch_number', 'card_coupon_number')
    def _check_credit_card_fields(self):
        for payment in self:
            # Skip validation for internal transfers, batch transfer payments, or when explicitly skipped
            if (payment.is_internal_transfer or 
                hasattr(payment, '_skip_card_validation') or 
                self.env.context.get('_skip_card_validation') or
                self.env.context.get('from_payment_wizard')):
                continue
                
            # Check if this payment belongs to a batch transfer
            batch_transfer = self.env['card.batch.transfer'].search([
                '|', 
                ('outbound_payment_id', '=', payment.id),
                ('inbound_payment_id', '=', payment.id)
            ], limit=1)
            
            # Skip validation for batch transfer related payments
            if batch_transfer:
                continue
                
            # Skip validation if payment is in a specific state that indicates it's from account_payment_pro
            if payment.state in ('posted', 'sent', 'reconciled'):
                continue
                
            if payment.journal_id and payment.journal_id.is_credit_card:
                if not payment.card_plan_id:
                    raise ValidationError(_('Credit Card Plan is required for credit card payments.'))
                if not payment.card_batch_number:
                    raise ValidationError(_('Batch Number is required for credit card payments.'))
                if not payment.card_coupon_number:
                    raise ValidationError(_('Coupon Number is required for credit card payments.'))

    def _create_paired_internal_transfer_payment(self):
        """When an internal transfer is posted, a paired payment is created
        with opposite payment_type and swapped journal_id & destination_journal_id.
        Both payments liquidity transfer lines are then reconciled.
        """
        for payment in self:
            paired_payment_type = "inbound" if payment.payment_type == "outbound" else "outbound"
            paired_payment = payment.copy(
                {
                    "journal_id": payment.destination_journal_id.id,
                    "company_id": payment.destination_journal_id.company_id.id,
                    "destination_journal_id": payment.journal_id.id,
                    "payment_type": paired_payment_type,
                    "payment_method_line_id": payment.destination_journal_id._get_available_payment_method_lines(
                        paired_payment_type
                    )[:1].id,
                    "move_id": None,
                    "memo": payment.memo,
                    "paired_internal_transfer_payment_id": payment.id,
                    "date": payment.date,
                }
            )
            # The payment method line ID in 'paired_payment' needs to be computed manually,
            # as it does not compute automatically.
            # This ensures not to use the same payment method line ID of the original transfer payment.
            paired_payment._compute_payment_method_line_id()
            if (
                not payment.payment_method_line_id.payment_account_id
                or not paired_payment.payment_method_line_id.payment_account_id
            ):
                raise ValidationError(
                    _("The origin or destination payment methods do not have an outstanding account.")
                )
            paired_payment.filtered(lambda p: not p.move_id)._generate_journal_entry()
            paired_payment.move_id._post(soft=False)
            payment.paired_internal_transfer_payment_id = paired_payment
            body = _("This payment has been created from: ") + payment._get_html_link()
            paired_payment.message_post(body=body)
            body = _("A paired payment has been created: ") + paired_payment._get_html_link()
            payment.message_post(body=body)

            # Reconcile the outstanding account lines
            lines = (payment.move_id.line_ids + paired_payment.move_id.line_ids).filtered(
                lambda l: l.account_id == payment.destination_journal_id.inbound_payment_method_line_ids.filtered(
                    lambda line: line.payment_account_id
                )[:1].payment_account_id and not l.reconciled
            )
            if lines:
                lines.reconcile()

    def action_post(self):
        """Override para crear registro de acreditación"""
        result = super().action_post()
        
        # Create paired internal transfer payment if needed
        self.filtered(
            lambda pay: pay.is_internal_transfer and not pay.paired_internal_transfer_payment_id
        )._create_paired_internal_transfer_payment()
        
        for payment in self:
            # Skip accreditation creation for internal transfers
            if payment.is_internal_transfer:
                continue
                
            if payment.journal_id.is_credit_card and payment.card_plan_id:
                payment._create_accreditation_record()
        
        # Update related batch transfers when payment is posted
        for payment in self:
            payment._update_related_batch_transfers()
        
        return result

    def write(self, vals):
        """Override write to detect reconciliation changes"""
        result = super().write(vals)
        
        # Check if reconciliation status or state changed
        if 'is_reconciled' in vals or any(field in vals for field in ['state']):
            for payment in self:
                # Handle internal transfer payments
                if payment.is_internal_transfer and payment.payment_type == 'inbound':
                    if (payment.is_reconciled and payment.state in ('posted', 'paid')) or payment.state in ('posted', 'paid'):
                        payment._update_batch_transfer_reconciliation_status(reconciled=True)
                    elif not payment.is_reconciled:
                        payment._update_batch_transfer_reconciliation_status(reconciled=False)
                
                # Handle regular inbound payments that may be related to batch transfers
                elif (payment.payment_type == 'inbound' and 
                      not payment.is_internal_transfer):
                    if payment.state in ('posted', 'paid'):  # When payment is posted/paid, mark batch as reconciled
                        payment._update_batch_transfer_from_payment_reconciliation(reconciled=True)
                    elif payment.state in ('cancel', 'draft'):
                        payment._update_batch_transfer_from_payment_reconciliation(reconciled=False)
                
                # Handle batch transfers where this payment is the inbound_payment_id
                payment._update_related_batch_transfers()
        
        return result

    def action_unreconcile(self):
        """Override to handle batch transfer reconciliation status"""
        result = super().action_unreconcile()
        
        # Update batch transfer accreditations when payment is unreconciled
        for payment in self:
            if payment.is_internal_transfer and payment.payment_type == 'inbound':
                payment._update_batch_transfer_reconciliation_status(reconciled=False)
            elif payment.payment_type == 'inbound' and not payment.is_internal_transfer:
                payment._update_batch_transfer_from_payment_reconciliation(reconciled=False)
        
        return result

    def _update_batch_transfer_reconciliation_status(self, reconciled=True):
        """Update the reconciliation status of related batch transfer accreditations"""
        self.ensure_one()
        
        if not self.is_internal_transfer:
            return
            
        # Find the batch transfer related to this payment
        batch_transfers = self.env['card.batch.transfer'].search([
            '|', 
            ('outbound_payment_id', '=', self.id),
            ('inbound_payment_id', '=', self.id)
        ])
        
        for batch_transfer in batch_transfers:
            if reconciled:
                batch_transfer.action_mark_accreditations_reconciled()
            else:
                batch_transfer.action_mark_accreditations_credited()

    def _update_batch_transfer_from_payment_reconciliation(self, reconciled=True):
        """Update batch transfer status when a regular inbound payment state changes"""
        self.ensure_one()
        
        # Find accreditations related to this payment
        accreditations = self.env['card.accreditation'].search([
            ('payment_id', '=', self.id)
        ])
        
        # Find batch transfers that contain these accreditations
        batch_transfers = self.env['card.batch.transfer'].search([
            ('accreditation_ids', 'in', accreditations.ids)
        ])
        
        for batch_transfer in batch_transfers:
            # Check if all payments in this batch transfer are in the right state
            if reconciled:
                # Get all accreditations in the batch transfer
                all_payments = batch_transfer.accreditation_ids.mapped('payment_id')
                # Check if all inbound payments are posted/paid
                inbound_payments = all_payments.filtered(lambda p: p.payment_type == 'inbound')
                
                if inbound_payments and all(p.state in ('posted', 'paid') for p in inbound_payments):
                    # All inbound payments are posted/paid, mark batch as reconciled
                    if batch_transfer.state == 'transferred':
                        batch_transfer.state = 'reconciled'
            else:
                # If any payment becomes unposted, revert to credited or transferred state
                if batch_transfer.state == 'reconciled':
                    batch_transfer.state = 'transferred'

    def _create_accreditation_record(self):
        """Crea registro en el modelo de acreditaciones"""
        self.ensure_one()
        
        self.env['card.accreditation'].create({
            'payment_id': self.id,
            'partner_id': self.partner_id.id,
            'journal_id': self.journal_id.id,
            'card_plan_id': self.card_plan_id.id,
            'batch_number': self.card_batch_number,
            'coupon_number': self.card_coupon_number,
            'collection_date': self.date,
            'original_amount': self.amount,
            'estimated_accreditation_date': self.estimated_accreditation_date,
            'estimated_liquidation_amount': self.estimated_liquidation_amount,
            'currency_id': self.currency_id.id,
        })

    def _update_related_batch_transfers(self):
        """Update batch transfers that have this payment as inbound_payment_id"""
        self.ensure_one()
        
        # Find batch transfers where this payment is the inbound payment
        batch_transfers = self.env['card.batch.transfer'].search([
            ('inbound_payment_id', '=', self.id)
        ])
        
        for batch_transfer in batch_transfers:
            # Force recompute of payment paid status and state
            batch_transfer._compute_is_payment_paid()
            batch_transfer._compute_inbound_payment_state()
            
            # Auto-update batch transfer state based on payment state
            if self.state == 'in_process' and batch_transfer.state == 'reconciled':
                # Payment was unreconciled, batch should go back to transferred
                batch_transfer.state = 'transferred'
                batch_transfer.message_post(
                    body=f"Batch transfer automatically updated to 'transferred' because inbound payment {self.name} was unreconciled (state: {self.state})",
                    message_type='notification'
                )
            elif (self.state == 'posted' and self.is_reconciled and 
                  batch_transfer.state == 'transferred'):
                # Payment is fully reconciled, batch should go to reconciled
                batch_transfer.state = 'reconciled'
                batch_transfer.message_post(
                    body=f"Batch transfer automatically updated to 'reconciled' because inbound payment {self.name} is fully reconciled",
                    message_type='notification'
                )

    def action_draft(self):
        """Override to prevent setting to draft if accreditations are in batch transfers"""
        # Check if any related accreditations are in batch transfers
        accreditations_in_batches = self.env['card.accreditation'].search([
            ('payment_id', 'in', self.ids),
            ('batch_transfer_id', '!=', False),
            ('batch_transfer_id.state', '!=', 'draft')
        ])
        
        if accreditations_in_batches:
            batch_transfers = accreditations_in_batches.mapped('batch_transfer_id')
            batch_names = ', '.join(batch_transfers.mapped('name'))
            raise UserError(_(
                "Cannot set payment to draft because it has accreditations included in batch transfers "
                "that are not in draft state: %s. "
                "Please set those batch transfers to draft first."
            ) % batch_names)
        
        result = super().action_draft()
        
        # Update related accreditations to pending state (since they follow payment state)
        related_accreditations = self.env['card.accreditation'].search([
            ('payment_id', 'in', self.ids)
        ])
        related_accreditations.write({'state': 'pending'})
        
        return result

    def unlink(self):
        """Override to delete related accreditations"""
        # Find related accreditations before deleting the payment
        related_accreditations = self.env['card.accreditation'].search([
            ('payment_id', 'in', self.ids)
        ])
        
        # Delete accreditations first (they have ondelete='cascade' but let's be explicit)
        if related_accreditations:
            related_accreditations.unlink()
        
        return super().unlink()