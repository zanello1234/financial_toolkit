# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountAccount(models.Model):
    _inherit = 'account.account'

    assigned_partner_ids = fields.Many2many(
        'res.partner',
        'account_partner_assignment_rel',
        'account_id',
        'partner_id',
        string='Assigned Partners',
        help="Partners assigned to this account. When a partner is assigned, "
             "their default payable/receivable account will be updated automatically."
    )

    @api.constrains('assigned_partner_ids', 'account_type')
    def _check_account_type_for_partner_assignment(self):
        """Ensure only payable/receivable accounts can have assigned partners"""
        for account in self:
            if account.assigned_partner_ids and account.account_type not in [
                'asset_receivable', 'liability_payable'
            ]:
                raise ValidationError(_(
                    "Only receivable and payable accounts can have assigned partners. "
                    "Account '%s' is of type '%s'."
                ) % (account.name, account.account_type))

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle partner assignment"""
        accounts = super().create(vals_list)
        for account in accounts:
            if account.assigned_partner_ids:
                account._update_partner_accounts()
        return accounts

    def write(self, vals):
        """Override write to handle partner assignment changes"""
        old_partners = {}
        if 'assigned_partner_ids' in vals:
            # Store old partner assignments before update
            for account in self:
                old_partners[account.id] = account.assigned_partner_ids.ids

        result = super().write(vals)

        if 'assigned_partner_ids' in vals:
            for account in self:
                # Skip conflict cleaning if we're in a recursive call
                if not self.env.context.get('skip_clean_conflicts'):
                    # Get newly assigned partners
                    new_partner_ids = set(account.assigned_partner_ids.ids)
                    old_partner_ids = set(old_partners.get(account.id, []))
                    
                    # Partners that were added
                    added_partner_ids = new_partner_ids - old_partner_ids
                    
                    if added_partner_ids and account.account_type == 'liability_payable':
                        # For payable accounts, ensure no partner is assigned to multiple payable accounts
                        account._clean_conflicting_payable_assignments(list(added_partner_ids))
                    
                    if added_partner_ids:
                        account._update_partner_accounts(partner_ids=list(added_partner_ids))
                
        return result

    def _clean_conflicting_payable_assignments(self, partner_ids):
        """Remove partners from other payable accounts to ensure single assignment rule"""
        self.ensure_one()
        
        if self.account_type != 'liability_payable':
            return
        
        partners = self.env['res.partner'].browse(partner_ids)
        
        for partner in partners:
            # Find other payable accounts where this partner is assigned
            other_payable_accounts = self.env['account.account'].search([
                ('id', '!=', self.id),
                ('account_type', '=', 'liability_payable'),
                ('assigned_partner_ids', 'in', [partner.id])
            ])
            
            # Remove partner from other payable accounts
            for other_account in other_payable_accounts:
                remaining_partners = other_account.assigned_partner_ids - partner
                other_account.with_context(skip_clean_conflicts=True).write({
                    'assigned_partner_ids': [(6, 0, remaining_partners.ids)]
                })

    def _update_partner_accounts(self, partner_ids=None):
        """Update assigned partners' default accounts"""
        self.ensure_one()
        
        if not partner_ids:
            partner_ids = self.assigned_partner_ids.ids
        
        partners = self.env['res.partner'].browse(partner_ids)
        
        for partner in partners:
            vals = {}
            if self.account_type == 'asset_receivable':
                vals['property_account_receivable_id'] = self.id
            elif self.account_type == 'liability_payable':
                vals['property_account_payable_id'] = self.id
            
            if vals:
                partner.write(vals)

    @api.model
    def clean_all_payable_conflicts(self):
        """Clean all existing conflicts where partners are assigned to multiple payable accounts"""
        # Get all partners that are assigned to multiple payable accounts
        partners_with_conflicts = self.env['res.partner'].search([])
        
        conflicts_found = []
        for partner in partners_with_conflicts:
            payable_accounts = partner.assigned_account_ids.filtered(
                lambda acc: acc.account_type == 'liability_payable'
            )
            
            if len(payable_accounts) > 1:
                # Keep only the first payable account, remove from others
                accounts_to_keep = payable_accounts[0]
                accounts_to_remove_from = payable_accounts[1:]
                
                for account in accounts_to_remove_from:
                    remaining_partners = account.assigned_partner_ids - partner
                    account.with_context(skip_clean_conflicts=True).write({
                        'assigned_partner_ids': [(6, 0, remaining_partners.ids)]
                    })
                
                conflicts_found.append({
                    'partner': partner.name,
                    'kept_account': accounts_to_keep.name,
                    'removed_from': accounts_to_remove_from.mapped('name')
                })
        
        return conflicts_found

    def action_assign_partners(self):
        """Action to open partner assignment wizard"""
        return {
            'name': _('Assign Partners'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.partner.assignment.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_account_id': self.id,
                'default_partner_ids': [(6, 0, self.assigned_partner_ids.ids)],
            }
        }