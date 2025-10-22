# © 2025 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CardTransferWizard(models.TransientModel):
    _name = 'card.transfer.wizard'
    _description = 'Credit Card Liquidity Transfer Wizard'

    journal_id = fields.Many2one(
        'account.journal',
        string='Credit Card Journal',
        required=True,
        domain=[('is_credit_card', '=', True)]
    )
    
    final_bank_journal_id = fields.Many2one(
        'account.journal',
        string='Final Bank Journal',
        required=True,
        domain=[('type', '=', 'bank')]
    )
    
    transfer_amount = fields.Monetary(
        string='Transfer Amount',
        required=True,
        currency_field='currency_id',
        help='Net amount to transfer after reconciliation'
    )
    
    transfer_date = fields.Date(
        string='Transfer Date',
        default=fields.Date.context_today,
        required=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )
    
    transfer_liquidity_account_id = fields.Many2one(
        'account.account',
        string='Transfer Liquidity Account',
        required=True,
        help='Bridge account for the transfer'
    )
    
    reference = fields.Char(
        string='Reference',
        help='Reference for the transfer movement'
    )
    
    notes = fields.Text(
        string='Notes',
        help='Additional notes for the transfer'
    )

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        """Actualizar cuenta de transferencia y banco final"""
        if self.journal_id:
            self.transfer_liquidity_account_id = self.journal_id.transfer_liquidity_account_id
            self.final_bank_journal_id = self.journal_id.final_bank_journal_id

    def action_create_transfer(self):
        """Crear la transferencia de liquidez"""
        self.ensure_one()
        
        if not self.transfer_liquidity_account_id:
            raise UserError(_('Please configure a Transfer Liquidity Account for the credit card journal.'))
        
        # Crear movimiento de salida del diario de tarjeta
        self._create_transfer_move()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Transfer Created'),
                'message': _('Liquidity transfer has been successfully created.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def _create_transfer_move(self):
        """Crear el asiento de transferencia"""
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': self.transfer_date,
            'ref': self.reference or _('Credit Card Liquidity Transfer'),
            'line_ids': [
                # Línea de débito en cuenta de transferencia
                (0, 0, {
                    'account_id': self.transfer_liquidity_account_id.id,
                    'name': _('Transfer to %s') % self.final_bank_journal_id.name,
                    'debit': self.transfer_amount,
                    'credit': 0,
                }),
                # Línea de crédito en cuenta del banco de tarjeta
                (0, 0, {
                    'account_id': self.journal_id.default_account_id.id,
                    'name': _('Transfer from %s') % self.journal_id.name,
                    'debit': 0,
                    'credit': self.transfer_amount,
                }),
            ]
        }
        
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        
        # Crear movimiento de entrada en el banco final
        final_move_vals = {
            'journal_id': self.final_bank_journal_id.id,
            'date': self.transfer_date,
            'ref': self.reference or _('Credit Card Liquidity Transfer'),
            'line_ids': [
                # Línea de débito en cuenta del banco final
                (0, 0, {
                    'account_id': self.final_bank_journal_id.default_account_id.id,
                    'name': _('Transfer from %s') % self.journal_id.name,
                    'debit': self.transfer_amount,
                    'credit': 0,
                }),
                # Línea de crédito en cuenta de transferencia
                (0, 0, {
                    'account_id': self.transfer_liquidity_account_id.id,
                    'name': _('Transfer to %s') % self.final_bank_journal_id.name,
                    'debit': 0,
                    'credit': self.transfer_amount,
                }),
            ]
        }
        
        final_move = self.env['account.move'].create(final_move_vals)
        final_move.action_post()
        
        return move, final_move

    @api.model
    def default_get(self, fields_list):
        """Configurar valores por defecto"""
        result = super().default_get(fields_list)
        
        journal_id = self.env.context.get('active_id')
        if journal_id:
            journal = self.env['account.journal'].browse(journal_id)
            if journal.is_credit_card:
                result.update({
                    'journal_id': journal.id,
                    'final_bank_journal_id': journal.final_bank_journal_id.id,
                    'transfer_liquidity_account_id': journal.transfer_liquidity_account_id.id,
                })
        
        return result