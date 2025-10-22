# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountPartnerAssignmentWizard(models.TransientModel):
    _name = 'account.partner.assignment.wizard'
    _description = 'Partner Assignment Wizard'

    account_id = fields.Many2one(
        'account.account',
        string='Account',
        required=True,
        domain=[('account_type', 'in', ['asset_receivable', 'liability_payable'])]
    )
    partner_ids = fields.Many2many(
        'res.partner',
        string='Partners to Assign',
        help="Select partners to assign to this account"
    )
    action_type = fields.Selection([
        ('add', 'Add Partners'),
        ('replace', 'Replace All Partners'),
        ('remove', 'Remove Partners')
    ], string='Action', default='add', required=True)

    @api.onchange('account_id')
    def _onchange_account_id(self):
        """Load current assigned partners when account changes"""
        if self.account_id:
            self.partner_ids = [(6, 0, self.account_id.assigned_partner_ids.ids)]

    def action_assign_partners(self):
        """Execute partner assignment based on selected action"""
        self.ensure_one()
        
        if not self.account_id:
            raise ValidationError(_("Please select an account."))
        
        if self.action_type in ['add', 'replace'] and not self.partner_ids:
            raise ValidationError(_("Please select at least one partner."))
        
        current_partners = self.account_id.assigned_partner_ids
        
        # For payable accounts, handle the single account per partner rule
        if self.account_id.account_type == 'liability_payable' and self.action_type in ['add', 'replace']:
            self._handle_payable_account_assignment()
        
        if self.action_type == 'add':
            # Add new partners to existing ones
            new_partners = current_partners | self.partner_ids
            self.account_id.assigned_partner_ids = [(6, 0, new_partners.ids)]
            
        elif self.action_type == 'replace':
            # Replace all partners
            self.account_id.assigned_partner_ids = [(6, 0, self.partner_ids.ids)]
            
        elif self.action_type == 'remove':
            # Remove selected partners
            remaining_partners = current_partners - self.partner_ids
            self.account_id.assigned_partner_ids = [(6, 0, remaining_partners.ids)]
        
        # Show success message
        message = self._get_success_message()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': message,
                'type': 'success',
                'sticky': False,
            }
        }

    def _handle_payable_account_assignment(self):
        """Handle automatic removal from other payable accounts"""
        partners_to_move = self.partner_ids
        
        # Find other payable accounts that have these partners assigned
        other_payable_accounts = self.env['account.account'].search([
            ('id', '!=', self.account_id.id),
            ('account_type', '=', 'liability_payable'),
            ('assigned_partner_ids', 'in', partners_to_move.ids)
        ])
        
        removed_info = []
        for other_account in other_payable_accounts:
            partners_to_remove = other_account.assigned_partner_ids & partners_to_move
            if partners_to_remove:
                # Remove partners from other account
                remaining_partners = other_account.assigned_partner_ids - partners_to_remove
                other_account.assigned_partner_ids = [(6, 0, remaining_partners.ids)]
                removed_info.append({
                    'account': other_account.name,
                    'partners': partners_to_remove.mapped('name')
                })
        
        # Show information about automatic removals
        if removed_info:
            removal_messages = []
            for info in removed_info:
                removal_messages.append(
                    f"• {', '.join(info['partners'])} removed from {info['account']}"
                )
            
            # Store the removal info to show in the success message
            self._removal_info = removal_messages

    def _get_success_message(self):
        """Get success message based on action type"""
        partner_count = len(self.partner_ids)
        
        if self.action_type == 'add':
            message = _("%d partner(s) added to account %s") % (
                partner_count, self.account_id.name
            )
        elif self.action_type == 'replace':
            message = _("Partners replaced for account %s (%d partner(s))") % (
                self.account_id.name, partner_count
            )
        elif self.action_type == 'remove':
            message = _("%d partner(s) removed from account %s") % (
                partner_count, self.account_id.name
            )
        
        # Add removal information if there were automatic removals
        if hasattr(self, '_removal_info') and self._removal_info:
            message += _("\n\nAutomatic removals from other payable accounts:\n%s") % '\n'.join(self._removal_info)
        
        return message