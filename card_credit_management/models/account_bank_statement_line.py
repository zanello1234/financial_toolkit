# © 2025 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    card_batch_search = fields.Char(
        string='Batch Search',
        compute='_compute_card_batch_search',
        search='_search_card_batch_search',
        help='Virtual field for searching by batch number in accreditations'
    )

    def _compute_card_batch_search(self):
        """Compute virtual field for batch search"""
        for line in self:
            # Extract potential batch number from payment reference or narration
            batch_info = []
            if line.payment_ref:
                # Look for patterns like "Lote 047", "LOTE047", etc.
                import re
                batch_matches = re.findall(r'lote\s*(\d+)', line.payment_ref.lower())
                batch_info.extend(batch_matches)
            
            line.card_batch_search = ', '.join(batch_info) if batch_info else ''

    def _search_card_batch_search(self, operator, value):
        """Search method for batch search field"""
        if not value:
            return []
        
        # Search in related accreditations
        accreditations = self.env['card.accreditation'].search([
            ('batch_number', operator, value)
        ])
        
        if not accreditations:
            return [('id', '=', False)]  # No results
        
        # Find statement lines that could match these accreditations
        # This is a simplified search - in practice you might want more sophisticated matching
        return [('payment_ref', 'ilike', f'lote%{value}%')]

    def action_reconcile_with_accreditation(self):
        """Action to reconcile with specific accreditation"""
        self.ensure_one()
        
        # Search for matching accreditations
        domain = []
        if self.payment_ref:
            import re
            batch_matches = re.findall(r'lote\s*(\d+)', self.payment_ref.lower())
            if batch_matches:
                domain.append(('batch_number', 'in', batch_matches))
        
        if not domain:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Batch Found'),
                    'message': _('Could not extract batch number from payment reference.'),
                    'type': 'warning',
                }
            }
        
        accreditations = self.env['card.accreditation'].search(domain + [('state', '!=', 'reconciled')])
        
        if not accreditations:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Accreditations Found'),
                    'message': _('No matching accreditations found for this batch.'),
                    'type': 'warning',
                }
            }
        
        # Open accreditations for selection
        return {
            'name': _('Select Accreditation to Reconcile'),
            'type': 'ir.actions.act_window',
            'res_model': 'card.accreditation',
            'view_mode': 'list,form',
            'domain': [('id', 'in', accreditations.ids)],
            'target': 'new',
        }