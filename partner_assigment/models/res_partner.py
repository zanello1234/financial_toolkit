# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    assigned_account_ids = fields.Many2many(
        'account.account',
        'account_partner_assignment_rel',
        'partner_id',
        'account_id',
        string='Assigned Accounts',
        help="Accounts where this partner is specifically assigned",
        readonly=True
    )

    @api.model
    def create(self, vals):
        """Override create to handle account assignment notifications"""
        partner = super().create(vals)
        return partner

    def write(self, vals):
        """Override write to log account changes"""
        result = super().write(vals)
        
        # Log if receivable/payable accounts were changed
        if 'property_account_receivable_id' in vals or 'property_account_payable_id' in vals:
            for partner in self:
                partner._log_account_change(vals)
        
        return result

    def _log_account_change(self, vals):
        """Log account changes for auditing purposes"""
        # This method can be extended to add logging functionality
        # For now, we'll just pass
        pass