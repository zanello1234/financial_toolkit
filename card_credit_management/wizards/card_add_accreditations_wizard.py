# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CardAddAccreditationsWizard(models.TransientModel):
    _name = 'card.add.accreditations.wizard'
    _description = 'Add Accreditations to Batch Transfer'

    batch_transfer_id = fields.Many2one(
        'card.batch.transfer',
        string='Batch Transfer',
        required=True,
        readonly=True
    )
    
    accreditation_ids = fields.Many2many(
        'card.accreditation',
        string='Accreditations to Add',
        domain="[('state', '=', 'pending'), ('journal_id', '=', source_journal_id), ('batch_transfer_id', '=', False)]",
        required=True
    )
    
    available_accreditation_ids = fields.Many2many(
        'card.accreditation',
        'wizard_available_accreditations_rel',
        string='Available Accreditations',
        domain="[('journal_id', '=', source_journal_id), ('batch_transfer_id', '=', False)]",
        readonly=True
    )
    
    source_journal_id = fields.Many2one(
        'account.journal',
        string='Source Journal',
        related='batch_transfer_id.source_journal_id',
        readonly=True
    )
    
    total_amount = fields.Monetary(
        string='Total Amount to Add',
        compute='_compute_total_amount',
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )
    
    @api.depends('accreditation_ids.net_amount')
    def _compute_total_amount(self):
        for wizard in self:
            wizard.total_amount = sum(wizard.accreditation_ids.mapped('net_amount'))
    
    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if 'batch_transfer_id' in res and res['batch_transfer_id']:
            batch_transfer = self.env['card.batch.transfer'].browse(res['batch_transfer_id'])
            available_accreditations = self.env['card.accreditation'].search([
                ('journal_id', '=', batch_transfer.source_journal_id.id),
                ('batch_transfer_id', '=', False),
            ])
            res['available_accreditation_ids'] = [(6, 0, available_accreditations.ids)]
        return res
    
    def action_refresh_available_accreditations(self):
        """Refresh the list of available accreditations"""
        available_accreditations = self.env['card.accreditation'].search([
            ('journal_id', '=', self.batch_transfer_id.source_journal_id.id),
            ('batch_transfer_id', '=', False),
        ])
        self.available_accreditation_ids = [(6, 0, available_accreditations.ids)]
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
    
    def action_add_accreditations(self):
        """Add selected accreditations to the batch transfer"""
        self.ensure_one()
        
        # First validate batch transfer state
        if self.batch_transfer_id.state != 'draft':
            raise UserError(_(
                "Cannot add accreditations to batch transfer '%s' because it is in '%s' state.\n\n"
                "Accreditations can only be added to batch transfers in 'draft' state.\n"
                "Please use the 'Back to Draft' button on the batch transfer first."
            ) % (self.batch_transfer_id.name, dict(self.batch_transfer_id._fields['state'].selection).get(self.batch_transfer_id.state, self.batch_transfer_id.state)))
        
        if not self.accreditation_ids:
            raise UserError(_("Please select at least one accreditation to add."))
        
        # Validate that all accreditations are pending and from the same journal
        invalid_accreditations = self.accreditation_ids.filtered(
            lambda acc: acc.state != 'pending' or 
                       acc.journal_id != self.batch_transfer_id.source_journal_id or
                       acc.batch_transfer_id
        )
        
        if invalid_accreditations:
            invalid_reasons = []
            for acc in invalid_accreditations:
                reasons = []
                if acc.state != 'pending':
                    reasons.append(f"state is '{acc.state}' (must be 'pending')")
                if acc.journal_id != self.batch_transfer_id.source_journal_id:
                    reasons.append(f"journal is '{acc.journal_id.name}' (must be '{self.batch_transfer_id.source_journal_id.name}')")
                if acc.batch_transfer_id:
                    reasons.append(f"already in batch transfer '{acc.batch_transfer_id.name}'")
                invalid_reasons.append(f"• {acc.display_name}: {', '.join(reasons)}")
            
            raise UserError(_(
                "Some selected accreditations are not valid for this batch transfer:\n\n%s\n\n"
                "Only pending accreditations from the same journal that are not already in a batch can be added."
            ) % '\n'.join(invalid_reasons))
        
        # Add accreditations to the batch transfer and mark as credited
        self.accreditation_ids.write({
            'batch_transfer_id': self.batch_transfer_id.id,
            'state': 'credited',
            'actual_accreditation_date': fields.Date.today()
        })
        # NOTE: Tax deductions auto-posting is handled automatically by the model's write method
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }