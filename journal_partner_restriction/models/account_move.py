from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.depends('journal_id', 'move_type')
    def _compute_allowed_partner_ids(self):
        """Compute allowed partners based on journal restrictions"""
        for move in self:
            allowed_partners = self.env['res.partner']
            
            # Debug info
            _logger = self.env.context.get('debug_partner_restriction', False)
            if _logger:
                print(f"Computing for move {move.id}: journal={move.journal_id.name if move.journal_id else 'None'}, restrict={move.journal_id.restrict_partners if move.journal_id else False}")
            
            if move.journal_id and move.journal_id.restrict_partners:
                if move.journal_id.allowed_partner_ids:
                    allowed_partners = move.journal_id.allowed_partner_ids
                    
                    # Filter by customer/supplier based on move type
                    if move.move_type in ('out_invoice', 'out_refund'):
                        allowed_partners = allowed_partners.filtered(lambda p: p.customer_rank > 0)
                    elif move.move_type in ('in_invoice', 'in_refund'):
                        allowed_partners = allowed_partners.filtered(lambda p: p.supplier_rank > 0)
                    
                    if _logger:
                        print(f"Restricted partners: {[p.name for p in allowed_partners]}")
                else:
                    # No partners configured, empty set
                    allowed_partners = self.env['res.partner']
                    if _logger:
                        print("No partners configured for restricted journal")
            else:
                # No restrictions - limit the search for better performance
                domain = []
                limit = 1000  # Reasonable limit
                
                if move.move_type in ('out_invoice', 'out_refund'):
                    domain = [('customer_rank', '>', 0)]
                elif move.move_type in ('in_invoice', 'in_refund'):
                    domain = [('supplier_rank', '>', 0)]
                else:
                    domain = ['|', ('customer_rank', '>', 0), ('supplier_rank', '>', 0)]
                
                allowed_partners = self.env['res.partner'].search(domain, limit=limit)
                
                if _logger:
                    print(f"No restrictions, found {len(allowed_partners)} partners")
            
            move.allowed_partner_ids = allowed_partners

    allowed_partner_ids = fields.Many2many(
        'res.partner',
        string='Allowed Partners',
        compute='_compute_allowed_partner_ids',
        store=False
    )

    @api.onchange('journal_id')
    def _onchange_journal_id_partner_restriction(self):
        """Update partner when journal changes and apply restrictions"""
        res = {}
        
        # Debug
        _logger = self.env.context.get('debug_partner_restriction', False)
        if _logger:
            print(f"Journal changed to: {self.journal_id.name if self.journal_id else 'None'}")
            print(f"Restrict partners: {self.journal_id.restrict_partners if self.journal_id else False}")
        
        if self.journal_id and self.journal_id.restrict_partners:
            if self.journal_id.allowed_partner_ids:
                # Build domain for allowed partners
                partner_ids = self.journal_id.allowed_partner_ids.ids
                domain = [('id', 'in', partner_ids)]
                
                # Add customer/supplier filter based on move type
                if self.move_type in ('out_invoice', 'out_refund'):
                    domain.append(('customer_rank', '>', 0))
                elif self.move_type in ('in_invoice', 'in_refund'):
                    domain.append(('supplier_rank', '>', 0))
                
                if _logger:
                    print(f"Applying domain: {domain}")
                
                # Check if current partner is still valid
                if self.partner_id and self.partner_id.id not in partner_ids:
                    self.partner_id = False
                    res['warning'] = {
                        'title': 'Partner Restriction',
                        'message': 'The selected partner is not allowed for this journal. Please select a different partner.'
                    }
                
                res['domain'] = {'partner_id': domain}
            else:
                # No partners allowed
                self.partner_id = False
                res['domain'] = {'partner_id': [('id', '=', False)]}
                res['warning'] = {
                    'title': 'No Partners Allowed',
                    'message': 'This journal has partner restrictions enabled but no partners are configured. Please configure allowed partners in the journal settings.'
                }
        else:
            # No restrictions, use standard domain
            domain = []
            if self.move_type in ('out_invoice', 'out_refund'):
                domain = [('customer_rank', '>', 0)]
            elif self.move_type in ('in_invoice', 'in_refund'):
                domain = [('supplier_rank', '>', 0)]
            
            if _logger:
                print(f"No restrictions, using domain: {domain}")
            
            if domain:
                res['domain'] = {'partner_id': domain}
        
        return res

    @api.onchange('move_type')
    def _onchange_move_type_partner_restriction(self):
        """Update partner domain when move type changes"""
        # Call the journal onchange to apply the updated domain
        return self._onchange_journal_id_partner_restriction()

    @api.onchange('partner_id')
    def _onchange_partner_id_check_restriction(self):
        """Check if selected partner is allowed for the journal"""
        if (self.journal_id and self.journal_id.restrict_partners and 
            self.partner_id and self.journal_id.allowed_partner_ids):
            if self.partner_id.id not in self.journal_id.allowed_partner_ids.ids:
                return {
                    'warning': {
                        'title': 'Partner Not Allowed',
                        'message': f'The partner "{self.partner_id.name}" is not allowed for journal "{self.journal_id.name}". Please select a different partner.'
                    }
                }

    @api.model
    def default_get(self, fields_list):
        """Override default_get to apply restrictions from the start"""
        res = super().default_get(fields_list)
        
        # If we have a default journal, check for restrictions
        if 'journal_id' in res and res['journal_id']:
            journal = self.env['account.journal'].browse(res['journal_id'])
            if journal.restrict_partners and not journal.allowed_partner_ids:
                # Clear partner_id if no partners are allowed
                res['partner_id'] = False
        
        return res

    @api.constrains('partner_id', 'journal_id')
    def _check_partner_journal_restriction(self):
        """Validate that partner is allowed for the journal"""
        for move in self:
            if (move.journal_id and move.journal_id.restrict_partners and 
                move.partner_id and move.journal_id.allowed_partner_ids):
                if move.partner_id.id not in move.journal_id.allowed_partner_ids.ids:
                    raise ValidationError(
                        f'The partner "{move.partner_id.name}" is not allowed for journal "{move.journal_id.name}". '
                        f'Please select a partner from the allowed list or update the journal configuration.'
                    )
    def _onchange_partner_id_check_restriction(self):
        """Check if selected partner is allowed for the journal"""
        if (self.journal_id and self.journal_id.restrict_partners and 
            self.partner_id and self.journal_id.allowed_partner_ids):
            if self.partner_id.id not in self.journal_id.allowed_partner_ids.ids:
                return {
                    'warning': {
                        'title': 'Partner Not Allowed',
                        'message': f'The partner "{self.partner_id.name}" is not allowed for journal "{self.journal_id.name}". Please select a different partner.'
                    }
                }

    @api.constrains('partner_id', 'journal_id')
    def _check_partner_journal_restriction(self):
        """Validate that partner is allowed for the journal"""
        for move in self:
            if (move.journal_id and move.journal_id.restrict_partners and 
                move.partner_id and move.journal_id.allowed_partner_ids):
                if move.partner_id.id not in move.journal_id.allowed_partner_ids.ids:
                    raise ValidationError(
                        f'The partner "{move.partner_id.name}" is not allowed for journal "{move.journal_id.name}". '
                        f'Please select a partner from the allowed list or update the journal configuration.'
                    )