# © 2025 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CardAddToBatchWizard(models.TransientModel):
    _name = 'card.add.to.batch.wizard'
    _description = 'Add Accreditations to Batch Transfer Wizard'

    accreditation_ids = fields.Many2many(
        'card.accreditation',
        string='Accreditations to Add',
        readonly=True
    )
    
    batch_transfer_id = fields.Many2one(
        'card.batch.transfer',
        string='Batch Transfer',
        required=True
    )
    
    accreditation_count = fields.Integer(
        string='Number of Accreditations',
        compute='_compute_accreditation_count'
    )
    
    total_amount = fields.Monetary(
        string='Total Amount',
        compute='_compute_total_amount',
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    @api.depends('accreditation_ids')
    def _compute_accreditation_count(self):
        for wizard in self:
            wizard.accreditation_count = len(wizard.accreditation_ids)

    @api.depends('accreditation_ids')
    def _compute_total_amount(self):
        for wizard in self:
            wizard.total_amount = sum(wizard.accreditation_ids.mapped('net_amount'))

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        return res

    @api.onchange('accreditation_ids')
    def _onchange_accreditation_ids(self):
        """Update domain for batch_transfer_id based on selected accreditations"""
        if self.accreditation_ids:
            # Get the journal from the first accreditation
            journal_id = self.accreditation_ids[0].journal_id.id
            return {
                'domain': {
                    'batch_transfer_id': [
                        ('state', 'in', ['draft', 'confirmed']),
                        ('source_journal_id', '=', journal_id)
                    ]
                }
            }
        return {'domain': {'batch_transfer_id': [('state', 'in', ['draft', 'confirmed'])]}}

    def action_add_to_batch(self):
        """Add the selected accreditations to the chosen batch transfer"""
        if not self.batch_transfer_id:
            raise UserError("Please select a batch transfer.")
        
        if not self.accreditation_ids:
            raise UserError("No accreditations selected.")
        
        # Verify accreditations are still valid (pending and not in batch)
        invalid_accreditations = self.accreditation_ids.filtered(
            lambda r: r.state != 'pending' or r.batch_transfer_id
        )
        
        if invalid_accreditations:
            raise UserError(
                f"Some accreditations are no longer valid for batch processing: "
                f"{', '.join(invalid_accreditations.mapped('display_name'))}"
            )
        
        # Add accreditations to the batch transfer and mark as credited
        self.accreditation_ids.write({
            'batch_transfer_id': self.batch_transfer_id.id,
            'state': 'credited',
            'actual_accreditation_date': fields.Date.today()
        })
        # NOTE: Tax deductions auto-posting is handled automatically by the model's write method
        
        # Show success message and return to batch transfer
        return {
            'type': 'ir.actions.act_window',
            'name': _('Batch Transfer'),
            'res_model': 'card.batch.transfer',
            'res_id': self.batch_transfer_id.id,
            'view_mode': 'form',
            'target': 'current',
        }