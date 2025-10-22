# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CardBatchTransferWizard(models.TransientModel):
    _name = 'card.batch.transfer.wizard'
    _description = 'Card Batch Transfer Wizard'

    source_journal_id = fields.Many2one(
        'account.journal',
        string='Source Journal (Credit Card)',
        required=True,
        domain="[('is_credit_card', '=', True)]",
        readonly=True
    )
    
    destination_journal_id = fields.Many2one(
        'account.journal',
        string='Destination Journal (Bank)',
        required=True,
        domain="[('type', '=', 'bank')]"
    )
    
    transfer_date = fields.Date(
        string='Transfer Date',
        default=fields.Date.context_today,
        required=True
    )
    
    accreditation_ids = fields.Many2many(
        'card.accreditation',
        string='Accreditations to Include',
        domain="[('state', '=', 'pending'), ('journal_id', '=', source_journal_id)]",
        required=True
    )
    
    total_amount = fields.Monetary(
        string='Total Transfer Amount',
        compute='_compute_total_amount',
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
        compute='_compute_accreditation_count'
    )
    
    notes = fields.Text(
        string='Transfer Notes'
    )
    
    @api.depends('accreditation_ids.net_amount')
    def _compute_total_amount(self):
        for wizard in self:
            wizard.total_amount = sum(wizard.accreditation_ids.mapped('net_amount'))
    
    @api.depends('accreditation_ids')
    def _compute_accreditation_count(self):
        for wizard in self:
            wizard.accreditation_count = len(wizard.accreditation_ids)
    
    @api.onchange('source_journal_id')
    def _onchange_source_journal_id(self):
        """Update destination journal and filter accreditations when source changes"""
        if self.source_journal_id:
            self.destination_journal_id = self.source_journal_id.final_bank_journal_id
            # Clear accreditations when journal changes
            self.accreditation_ids = False
    
    def action_create_batch_transfer(self):
        """Create the batch transfer"""
        self.ensure_one()
        
        if not self.accreditation_ids:
            raise UserError("Please select at least one accreditation for the batch transfer.")
        
        # Validate accreditations are still available
        unavailable = self.accreditation_ids.filtered(lambda a: a.state != 'pending')
        if unavailable:
            raise UserError(
                f"Some selected accreditations are no longer pending: "
                f"{', '.join(unavailable.mapped('name'))}"
            )
        
        # Create batch transfer
        transfer_vals = {
            'transfer_date': self.transfer_date,
            'source_journal_id': self.source_journal_id.id,
            'destination_journal_id': self.destination_journal_id.id,
            'notes': self.notes,
        }
        
        batch_transfer = self.env['card.batch.transfer'].create(transfer_vals)
        
        # Link accreditations to batch transfer and mark as credited
        self.accreditation_ids.write({
            'batch_transfer_id': batch_transfer.id,
            'state': 'credited',
            'actual_accreditation_date': fields.Date.today()
        })
        # NOTE: Tax deductions auto-posting is handled automatically by the model's write method
        
        # Automatically confirm the transfer
        batch_transfer.action_confirm()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Batch Transfer Created'),
            'res_model': 'card.batch.transfer',
            'res_id': batch_transfer.id,
            'view_mode': 'form',
            'target': 'current',
        }