from odoo import models, fields, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    restrict_partners = fields.Boolean(
        string='Restrict Partners',
        help='If enabled, only selected partners can be used with this journal',
        default=False
    )
    
    allowed_partner_ids = fields.Many2many(
        'res.partner',
        'journal_partner_rel',
        'journal_id',
        'partner_id',
        string='Allowed Partners',
        help='Partners that can be used with this journal when restriction is enabled'
    )

    @api.onchange('restrict_partners')
    def _onchange_restrict_partners(self):
        """Clear allowed partners when restriction is disabled"""
        if not self.restrict_partners:
            self.allowed_partner_ids = [(5, 0, 0)]  # Clear all partners

    def _check_journal_lock(self):
        """Override to allow modification of partner restriction fields even with posted entries"""
        # Get the original method behavior
        super()._check_journal_lock()
        
        # If we're only modifying partner restriction fields, allow the change
        if self.env.context.get('skip_lock_check_for_partner_restrictions'):
            return
        
        # Check if only partner restriction fields are being modified
        if hasattr(self, '_origin'):
            changed_fields = set()
            for field_name in self._fields:
                if (hasattr(self._origin, field_name) and 
                    getattr(self, field_name, None) != getattr(self._origin, field_name, None)):
                    changed_fields.add(field_name)
            
            # If only our fields are changing, skip the lock check
            partner_restriction_fields = {'restrict_partners', 'allowed_partner_ids'}
            if changed_fields.issubset(partner_restriction_fields):
                return
        
        # For any other field changes, apply the original lock check
        if self._has_accounting_entries():
            raise models.UserError(
                "You cannot modify a journal with posted entries. "
                "However, you can still modify partner restrictions."
            )

    def write(self, vals):
        """Override write to handle partner restriction fields specially"""
        partner_restriction_fields = {'restrict_partners', 'allowed_partner_ids'}
        
        # Check if we're only modifying partner restriction fields
        if set(vals.keys()).issubset(partner_restriction_fields):
            # Skip the journal lock check for partner restriction fields
            return super(AccountJournal, self.with_context(
                skip_lock_check_for_partner_restrictions=True
            )).write(vals)
        
        return super().write(vals)