# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class CardBatchTransfer(models.Model):
    _name = 'card.batch.transfer'
    _description = 'Credit Card Batch Transfer'
    _order = 'transfer_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Batch Transfer Reference',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New')
    )
    
    transfer_date = fields.Date(
        string='Transfer Date',
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )
    
    source_journal_id = fields.Many2one(
        'account.journal',
        string='Source Journal (Credit Card)',
        required=True,
        domain="[('is_credit_card', '=', True)]",
        tracking=True
    )
    
    destination_journal_id = fields.Many2one(
        'account.journal',
        string='Destination Journal (Bank)',
        required=True,
        domain="[('type', '=', 'bank')]",
        tracking=True
    )
    
    accreditation_ids = fields.One2many(
        'card.accreditation',
        'batch_transfer_id',
        string='Included Accreditations',
        readonly=True
    )
    
    total_amount = fields.Monetary(
        string='Total Transfer Amount',
        compute='_compute_total_amount',
        store=True,
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )
    
    accreditation_count = fields.Integer(
        string='Number of Accreditations',
        compute='_compute_accreditation_count',
        store=True
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('transferred', 'Transferred'),
        ('reconciled', 'Reconciled'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        readonly=True,
        tracking=True
    )
    
    # Paired payment fields following account_internal_transfer pattern
    outbound_payment_id = fields.Many2one(
        'account.payment',
        string='Outbound Payment',
        readonly=True,
        help='Payment from source journal (credit card)'
    )
    
    inbound_payment_id = fields.Many2one(
        'account.payment',
        string='Inbound Payment',
        readonly=True,
        help='Payment to destination journal (bank)'
    )
    
    is_payment_reconciled = fields.Boolean(
        string='Payment Reconciled',
        compute='_compute_is_payment_reconciled',
        store=True,
        help='True if the inbound payment is reconciled'
    )
    
    is_payment_paid = fields.Boolean(
        string='Payment Paid',
        compute='_compute_is_payment_paid',
        store=True,
        help='True if the inbound payment is in posted (paid) state'
    )
    
    inbound_payment_state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('paid', 'Paid'),
        ('in_process', 'In Process'),
        ('sent', 'Sent'),
        ('reconciled', 'Reconciled'),
        ('partial', 'Partially Reconciled'),
        ('cancel', 'Cancelled'),
    ], string='Inbound Payment State',
       compute='_compute_inbound_payment_state',
       store=True,
       readonly=True,
       help='Automatic state from inbound payment to control batch transfer status')
    
    destination_account_id = fields.Many2one(
        'account.account',
        string='Outstanding Account',
        readonly=True,
        help='Outstanding account used for the transfer'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    
    notes = fields.Text(
        string='Notes'
    )
    
    # Global deductions
    global_fee = fields.Monetary(
        string='Global Processing Fee',
        currency_field='currency_id',
        default=0.0,
        help='Global fee applied to the entire batch transfer'
    )
    
    global_tax_deductions = fields.Monetary(
        string='Global Tax Deductions',
        currency_field='currency_id',
        default=0.0,
        help='Global tax deductions (retentions, etc.) applied to the entire batch'
    )
    
    final_transfer_amount = fields.Monetary(
        string='Final Transfer Amount',
        compute='_compute_final_transfer_amount',
        store=True,
        currency_field='currency_id',
        help='Final amount after global deductions'
    )
    
    @api.depends('total_amount', 'global_fee', 'global_tax_deductions')
    def _compute_final_transfer_amount(self):
        for transfer in self:
            transfer.final_transfer_amount = transfer.total_amount - transfer.global_fee - transfer.global_tax_deductions
    
    @api.depends('inbound_payment_id', 'inbound_payment_id.is_reconciled')
    def _compute_is_payment_reconciled(self):
        for transfer in self:
            transfer.is_payment_reconciled = bool(
                transfer.inbound_payment_id and transfer.inbound_payment_id.is_reconciled
            )
    
    @api.depends('inbound_payment_id', 'inbound_payment_id.state')
    def _compute_is_payment_paid(self):
        """Compute if the inbound payment is in paid state and auto-update state"""
        for transfer in self:
            # Only consider 'paid' state, not 'posted'
            transfer.is_payment_paid = bool(
                transfer.inbound_payment_id and transfer.inbound_payment_id.state == 'paid'
            )
            
            # Auto-update batch transfer state based on payment state
            if transfer.is_payment_paid and transfer.state == 'transferred':
                # Use write to trigger accreditation updates
                transfer.write({'state': 'reconciled'})
            elif not transfer.is_payment_paid and transfer.state == 'reconciled':
                # Only revert if payment is cancelled or draft, not if it's just not posted yet
                if transfer.inbound_payment_id and transfer.inbound_payment_id.state in ('cancel', 'draft'):
                    # Use write to trigger accreditation updates
                    transfer.write({'state': 'transferred'})

    @api.depends('inbound_payment_id', 'inbound_payment_id.state')
    def _compute_inbound_payment_state(self):
        """Compute inbound payment state automatically from the actual payment"""
        for transfer in self:
            old_payment_state = transfer.inbound_payment_state
            if transfer.inbound_payment_id:
                transfer.inbound_payment_state = transfer.inbound_payment_id.state
            else:
                transfer.inbound_payment_state = 'draft'
            
            # Auto-update batch transfer state based on payment state changes
            self._auto_update_batch_state_from_payment(old_payment_state)
    
    def _auto_update_batch_state_from_payment(self, old_payment_state):
        """Automatically update batch transfer state when payment state changes"""
        for transfer in self:
            if not transfer.inbound_payment_id:
                continue
                
            current_payment_state = transfer.inbound_payment_state
            
            # When payment goes from 'posted' to 'in_process' (unreconciled), 
            # batch transfer should go back to 'transferred'
            if (old_payment_state == 'posted' and 
                current_payment_state == 'in_process' and 
                transfer.state == 'reconciled'):
                
                transfer.state = 'transferred'
                transfer.message_post(
                    body=f"Batch transfer automatically updated to 'transferred' because inbound payment was unreconciled (state: {current_payment_state})",
                    message_type='notification'
                )
            
            # When payment is reconciled (posted and reconciled), 
            # batch transfer should go to 'reconciled'  
            elif (current_payment_state == 'posted' and 
                  transfer.is_payment_reconciled and 
                  transfer.state == 'transferred'):
                
                transfer.state = 'reconciled'
                transfer.message_post(
                    body=f"Batch transfer automatically updated to 'reconciled' because inbound payment is fully reconciled",
                    message_type='notification'
                )
    
    @api.depends('accreditation_ids.net_amount')
    def _compute_total_amount(self):
        for transfer in self:
            transfer.total_amount = sum(transfer.accreditation_ids.mapped('net_amount'))
    
    @api.depends('accreditation_ids')
    def _compute_accreditation_count(self):
        for transfer in self:
            transfer.accreditation_count = len(transfer.accreditation_ids)
    
    @api.onchange('is_payment_reconciled')
    def _onchange_payment_reconciled(self):
        """Automatically update batch transfer state based on payment reconciliation"""
        if self.is_payment_reconciled and self.state == 'transferred':
            self.state = 'reconciled'
        elif not self.is_payment_reconciled and self.state == 'reconciled':
            self.state = 'transferred'
    
    @api.onchange('is_payment_paid')
    def _onchange_payment_paid(self):
        """Automatically update batch transfer state based on payment paid status"""
        if self.is_payment_paid and self.state == 'transferred':
            self.state = 'reconciled'
        elif not self.is_payment_paid and self.state == 'reconciled':
            self.state = 'transferred'
    
    def _update_accreditations_state_on_reconciled(self):
        """Helper method to update accreditations to reconciled state"""
        if hasattr(self, 'accreditation_ids') and self.accreditation_ids:
            self.accreditation_ids.filtered(lambda acc: acc.state == 'credited').write({
                'state': 'reconciled'
            })
    
    def _update_accreditations_state_on_transferred(self):
        """Helper method to update accreditations to credited state"""
        if hasattr(self, 'accreditation_ids') and self.accreditation_ids:
            self.accreditation_ids.filtered(lambda acc: acc.state == 'reconciled').write({
                'state': 'credited'
            })
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('card.batch.transfer') or _('New')
        return super().create(vals_list)
    
    def action_confirm(self):
        """Confirm the batch transfer"""
        for transfer in self:
            if transfer.state != 'draft':
                raise UserError("Only draft transfers can be confirmed.")
            if not transfer.accreditation_ids:
                raise UserError("Cannot confirm a transfer without accreditations.")
            
            transfer.state = 'confirmed'
    
    def action_transfer(self):
        """Execute the internal transfer using paired payment logic like account_internal_transfer"""
        for transfer in self:
            if transfer.state != 'confirmed':
                raise UserError("Only confirmed transfers can be executed.")
            
            # Create paired internal transfer payments following account_internal_transfer pattern
            transfer._create_paired_internal_transfer_payments()
            
            transfer.move_id = transfer.outbound_payment_id.move_id.id
            transfer.state = 'transferred'
            
            # Mark accreditations as credited
            for accreditation in transfer.accreditation_ids:
                accreditation.write({
                    'state': 'credited',
                    'actual_accreditation_date': transfer.transfer_date,
                    'actual_liquidation_amount': accreditation.net_amount,
                })
    
    def _create_paired_internal_transfer_payments(self):
        """Create paired internal transfer payments following account_internal_transfer pattern"""
        for transfer in self:
            # Validate that journals have outstanding accounts configured
            source_payment_method_line = transfer.source_journal_id.outbound_payment_method_line_ids.filtered(
                lambda l: l.payment_method_id.code == 'manual'
            )[:1]
            dest_payment_method_line = transfer.destination_journal_id.inbound_payment_method_line_ids.filtered(
                lambda l: l.payment_method_id.code == 'manual'  
            )[:1]
            
            if not source_payment_method_line.payment_account_id:
                raise ValidationError(
                    _("The source journal %s does not have an outstanding account configured for manual payment method.") 
                    % transfer.source_journal_id.name
                )
            
            if not dest_payment_method_line.payment_account_id:
                raise ValidationError(
                    _("The destination journal %s does not have an outstanding account configured for manual payment method.") 
                    % transfer.destination_journal_id.name
                )
            
            # Use the destination outstanding account for reconciliation
            destination_account = dest_payment_method_line.payment_account_id
            transfer.destination_account_id = destination_account.id
            
            # Create only the outbound payment - the paired payment will be created automatically by action_post
            outbound_payment = self.env['account.payment'].with_context(_skip_card_validation=True).create({
                'payment_type': 'outbound',
                'partner_type': 'supplier',
                'partner_id': False,  # No partner for internal transfers
                'journal_id': transfer.source_journal_id.id,
                'destination_journal_id': transfer.destination_journal_id.id,
                'payment_method_line_id': source_payment_method_line.id,
                'amount': transfer.final_transfer_amount,
                'currency_id': transfer.currency_id.id,
                'date': transfer.transfer_date,
                'memo': f'Batch Transfer: {transfer.name}',
                'is_internal_transfer': True,
            })
            
            # Post the outbound payment - this will automatically create the paired inbound payment
            outbound_payment.action_post()
            transfer.outbound_payment_id = outbound_payment.id
            
            # Get the automatically created inbound payment
            inbound_payment = outbound_payment.paired_internal_transfer_payment_id
            transfer.inbound_payment_id = inbound_payment.id
    
    def action_cancel(self):
        """Cancel the batch transfer and related payments"""
        for transfer in self:
            if transfer.state in ('transferred', 'reconciled'):
                raise UserError("Cannot cancel a transfer that has already been executed or reconciled.")
            
            # Cancel related payments if they exist
            if transfer.outbound_payment_id and transfer.outbound_payment_id.state not in ('cancel', 'reconciled'):
                transfer.outbound_payment_id.action_cancel()
            
            if transfer.inbound_payment_id and transfer.inbound_payment_id.state not in ('cancel', 'reconciled'):
                transfer.inbound_payment_id.action_cancel()
            
            transfer.state = 'cancelled'
    
    def action_set_to_draft(self):
        """Reset to draft"""
        for transfer in self:
            if transfer.state in ('transferred', 'reconciled'):
                raise UserError("Cannot reset a transfer that has been executed or reconciled.")
            
            # Move accreditations back to pending state when going to draft
            accreditations_to_reset = transfer.accreditation_ids.filtered(
                lambda acc: acc.state in ('credited', 'reconciled')
            )
            accreditations_to_reset.write({'state': 'pending'})
            
            transfer.state = 'draft'
            
            # Log the action if there were accreditations to reset
            if accreditations_to_reset:
                transfer.message_post(
                    body=f"Batch transfer set to draft. Reset {len(accreditations_to_reset)} accreditation(s) to pending state."
                )
    
    def action_back_to_draft(self):
        """Move back to draft state from transferred to allow adding more accreditations"""
        for transfer in self:
            if transfer.state != 'transferred':
                raise UserError("Only transferred batch transfers can be moved back to draft.")
            
            # Handle related payments - set to draft and remove references
            payments_to_remove = []
            
            if transfer.inbound_payment_id:
                payment = transfer.inbound_payment_id
                # Set payment to draft if not already
                if payment.state != 'draft':
                    try:
                        payment.action_draft()
                    except Exception:
                        # If can't set to draft, we'll delete it anyway
                        pass
                
                payments_to_remove.append(('inbound', payment))
                transfer.inbound_payment_id = False
            
            if transfer.outbound_payment_id:
                payment = transfer.outbound_payment_id
                # Set payment to draft if not already
                if payment.state != 'draft':
                    try:
                        payment.action_draft()
                    except Exception:
                        # If can't set to draft, we'll delete it anyway
                        pass
                
                payments_to_remove.append(('outbound', payment))
                transfer.outbound_payment_id = False
            
            # Delete the payments
            payment_names = []
            for payment_type, payment in payments_to_remove:
                payment_names.append(f"{payment_type} payment {payment.name}")
                payment.unlink()
            
            # Move accreditations back to pending state (removed from batch)
            accreditations_to_reset = transfer.accreditation_ids.filtered(
                lambda acc: acc.state in ('credited', 'reconciled')
            )
            accreditations_to_reset.write({'state': 'pending'})
            
            # Set transfer back to draft
            transfer.state = 'draft'
            
            # Log the action
            log_message = "Batch transfer moved back to draft state. More accreditations can now be added."
            if payment_names:
                log_message += f" Removed payments: {', '.join(payment_names)}."
            if accreditations_to_reset:
                log_message += f" Reset {len(accreditations_to_reset)} accreditation(s) to pending state."
            
            transfer.message_post(body=log_message)
    
    def action_view_journal_entry(self):
        """View the associated journal entry"""
        self.ensure_one()
        if not self.move_id:
            raise UserError("No journal entry found for this batch transfer.")
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Entry'),
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_outbound_payment(self):
        """View the outbound payment"""
        self.ensure_one()
        if not self.outbound_payment_id:
            raise UserError("No outbound payment found for this batch transfer.")
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Outbound Payment'),
            'res_model': 'account.payment',
            'res_id': self.outbound_payment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_inbound_payment(self):
        """View the inbound payment"""
        self.ensure_one()
        if not self.inbound_payment_id:
            raise UserError("No inbound payment found for this batch transfer.")
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Inbound Payment'),
            'res_model': 'account.payment',
            'res_id': self.inbound_payment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_view_payments(self):
        """View both payments"""
        self.ensure_one()
        
        payment_ids = []
        if self.outbound_payment_id:
            payment_ids.append(self.outbound_payment_id.id)
        if self.inbound_payment_id:
            payment_ids.append(self.inbound_payment_id.id)
        
        if not payment_ids:
            raise UserError("No payments found for this batch transfer.")
        
        if len(payment_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Transfer Payment'),
                'res_model': 'account.payment',
                'res_id': payment_ids[0],
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Transfer Payments'),
                'res_model': 'account.payment',
                'domain': [('id', 'in', payment_ids)],
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'target': 'current',
            }
    
    def action_add_accreditations(self):
        """Open wizard to add more accreditations to this batch transfer"""
        self.ensure_one()
        
        if self.state != 'draft':
            raise UserError(_(
                "Cannot add accreditations to batch transfer '%s' because it is in '%s' state.\n\n"
                "Accreditations can only be added to batch transfers in 'draft' state.\n"
                "If you need to modify this batch transfer, use the 'Back to Draft' button first."
            ) % (self.name, dict(self._fields['state'].selection).get(self.state, self.state)))
        
        # Get available accreditations for the same journal
        available_accreditations = self.env['card.accreditation'].search([
            ('state', '=', 'pending'),
            ('journal_id', '=', self.source_journal_id.id),
            ('batch_transfer_id', '=', False),  # Not already in a batch
        ])
        
        if not available_accreditations:
            raise UserError(_(
                "No pending accreditations available for journal '%s'.\n\n"
                "To add accreditations to this batch transfer, you need accreditations that are:\n"
                "• In 'pending' state\n"
                "• From the same journal (%s)\n"
                "• Not already included in another batch transfer"
            ) % (self.source_journal_id.name, self.source_journal_id.name))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Accreditations to Batch Transfer'),
            'res_model': 'card.add.accreditations.wizard',
            'view_mode': 'form',
            'context': {
                'default_batch_transfer_id': self.id,
                'available_accreditation_ids': available_accreditations.ids,
            },
            'target': 'new',
        }
    
    def unlink(self):
        """Prevent deletion of confirmed/transferred records and clean up related payments"""
        for transfer in self:
            if transfer.state in ('confirmed', 'transferred'):
                raise UserError("Cannot delete confirmed or transferred batch transfers.")
            
            # Delete related payments if they exist and are not reconciled
            if transfer.outbound_payment_id and transfer.outbound_payment_id.state not in ('reconciled',):
                transfer.outbound_payment_id.unlink()
            
            if transfer.inbound_payment_id and transfer.inbound_payment_id.state not in ('reconciled',):
                transfer.inbound_payment_id.unlink()
        
        return super().unlink()
    
    def action_mark_accreditations_reconciled(self):
        """Mark all accreditations in this batch transfer as reconciled"""
        for transfer in self:
            transfer.accreditation_ids.filtered(lambda acc: acc.state == 'credited').write({
                'state': 'reconciled'
            })
    
    def action_mark_accreditations_credited(self):
        """Mark all accreditations in this batch transfer as credited (back from reconciled)"""
        for transfer in self:
            transfer.accreditation_ids.filtered(lambda acc: acc.state == 'reconciled').write({
                'state': 'credited'
            })
    
    def action_check_reconciliation_status(self):
        """Check and display the current reconciliation status without automatic changes"""
        status_info = []
        
        for transfer in self:
            # Refresh calculated fields
            transfer._compute_is_payment_reconciled()
            transfer._compute_is_payment_paid()
            transfer._compute_inbound_payment_state()
            
            # Gather status information
            payment_info = "No inbound payment"
            if transfer.inbound_payment_id:
                payment_info = f"Payment state: {transfer.inbound_payment_state or 'unknown'}"
                if transfer.is_payment_paid:
                    payment_info += " (PAID - can be reconciled)"
                elif transfer.inbound_payment_state == 'posted':
                    payment_info += " (POSTED - not yet paid)"
                else:
                    payment_info += " (NOT READY for reconciliation)"
            
            status_info.append(f"Transfer {transfer.name}: {payment_info}")
        
        message = "\n".join(status_info)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Reconciliation Status Check',
                'message': message,
                'type': 'info',
                'sticky': True,
            }
        }
    
    def action_reconcile(self):
        """Mark the batch transfer as reconciled and update all accreditations"""
        for transfer in self:
            if transfer.state != 'transferred':
                raise UserError(_('Only transferred batch transfers can be reconciled.'))
            
            # Mark all accreditations as reconciled
            transfer.action_mark_accreditations_reconciled()
            
            # Update batch transfer state
            transfer.state = 'reconciled'
            
            # Post a message in the chatter
            transfer.message_post(
                body=_('Batch transfer has been reconciled. All included accreditations have been marked as reconciled.'),
                subtype_xmlid='mail.mt_note'
            )
    
    def action_unreoncile(self):
        """Mark the batch transfer as transferred (undo reconciliation)"""
        for transfer in self:
            if transfer.state != 'reconciled':
                raise UserError(_('Only reconciled batch transfers can be unreconciled.'))
            
            # Mark all accreditations as credited (undo reconciliation)
            transfer.action_mark_accreditations_credited()
            
            # Update batch transfer state back to transferred
            transfer.state = 'transferred'
            
            # Post a message in the chatter
            transfer.message_post(
                body=_('Batch transfer reconciliation has been undone. All included accreditations have been marked as credited.'),
                subtype_xmlid='mail.mt_note'
            )
    
    def write(self, vals):
        """Override write to trigger payment state check and accreditation updates"""
        # Store old state to detect changes
        old_states = {}
        if 'state' in vals:
            for transfer in self:
                old_states[transfer.id] = transfer.state
        
        result = super().write(vals)
        
        # If state is updated, update accreditations accordingly
        if 'state' in vals:
            for transfer in self:
                old_state = old_states.get(transfer.id)
                new_state = vals['state']
                
                # If state changed to reconciled, mark accreditations as reconciled
                if old_state == 'transferred' and new_state == 'reconciled':
                    transfer.action_mark_accreditations_reconciled()
                # If state changed from reconciled to transferred, mark accreditations as credited
                elif old_state == 'reconciled' and new_state == 'transferred':
                    transfer.action_mark_accreditations_credited()
                # If state changed to draft, reset accreditations to pending
                elif new_state == 'draft' and old_state != 'draft':
                    accreditations_to_reset = transfer.accreditation_ids.filtered(
                        lambda acc: acc.state in ('credited', 'reconciled')
                    )
                    if accreditations_to_reset:
                        accreditations_to_reset.write({'state': 'pending'})
                        # Log the automatic change
                        transfer.message_post(
                            body=f"Batch transfer state changed to draft. Automatically reset {len(accreditations_to_reset)} accreditation(s) to pending state."
                        )
        
        # If inbound_payment_id is updated, recompute payment state
        if 'inbound_payment_id' in vals:
            for transfer in self:
                transfer._compute_is_payment_paid()
                transfer._compute_inbound_payment_state()
        
        return result
    
    def action_sync_payment_state(self):
        """Manual action to refresh payment state display only"""
        for transfer in self:
            # Force recompute of the calculated fields
            transfer._compute_inbound_payment_state()
            transfer._compute_is_payment_paid()
            transfer._compute_is_payment_reconciled()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Payment State Refreshed',
                'message': 'Payment state has been refreshed from actual payment status.',
                'type': 'success',
                'sticky': False,
            }
        }