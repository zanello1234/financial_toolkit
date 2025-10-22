# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CardTaxTemplateWizard(models.TransientModel):
    _name = 'card.tax.template.wizard'
    _description = 'Tax Template Application Wizard'

    accreditation_id = fields.Many2one(
        'card.accreditation',
        string='Accreditation',
        readonly=True
    )
    
    accreditation_ids = fields.Many2many(
        'card.accreditation',
        string='Accreditations',
        readonly=True
    )
    
    is_bulk_operation = fields.Boolean(
        string='Bulk Operation',
        default=False
    )
    
    template_id = fields.Many2one(
        'card.tax.deduction.template',
        string='Tax Template',
        required=True,
        domain="[('active', '=', True)]"
    )
    
    template_line_ids = fields.One2many(
        related='template_id.tax_line_ids',
        string='Template Lines',
        readonly=True
    )
    
    preview_amount = fields.Monetary(
        string='Base Amount',
        compute='_compute_preview_amount',
        readonly=True
    )
    
    accreditation_count = fields.Integer(
        string='Number of Accreditations',
        compute='_compute_accreditation_count'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        readonly=True
    )
    
    @api.depends('accreditation_id.original_amount', 'accreditation_ids.original_amount')
    def _compute_preview_amount(self):
        for wizard in self:
            if wizard.is_bulk_operation and wizard.accreditation_ids:
                wizard.preview_amount = sum(wizard.accreditation_ids.mapped('original_amount'))
            elif wizard.accreditation_id:
                wizard.preview_amount = wizard.accreditation_id.original_amount
            else:
                wizard.preview_amount = 0.0
    
    @api.depends('accreditation_ids')
    def _compute_accreditation_count(self):
        for wizard in self:
            wizard.accreditation_count = len(wizard.accreditation_ids)
    
    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        context = self.env.context
        
        if context.get('bulk_operation'):
            res['is_bulk_operation'] = True
            if context.get('default_accreditation_ids'):
                res['accreditation_ids'] = context['default_accreditation_ids']
        elif context.get('active_id'):
            res['accreditation_id'] = context['active_id']
            
        return res
    
    @api.onchange('template_id')
    def _onchange_template_id(self):
        """Update preview when template changes"""
        # This will automatically update template_line_ids due to related field
        pass
    
    def action_apply_template(self):
        """Apply selected template to accreditation(s)"""
        self.ensure_one()
        
        if not self.template_id.tax_line_ids:
            raise UserError("Selected template has no tax lines configured.")
        
        # Determine which accreditations to process
        if self.is_bulk_operation:
            accreditations = self.accreditation_ids
            if not accreditations:
                raise UserError("No accreditations selected for bulk operation.")
        else:
            accreditations = self.accreditation_id
            if not accreditations:
                raise UserError("No accreditation specified.")
        
        # Create deductions for each accreditation
        created_deductions = self.env['card.tax.deduction']
        processed_count = 0
        
        for accreditation in accreditations:
            # Create deductions for each tax line
            for tax_line in self.template_id.tax_line_ids:
                deduction_vals = {
                    'name': f"{self.template_id.name} - {tax_line.name}",
                    'accreditation_id': accreditation.id,
                    'tax_account_id': tax_line.tax_account_id.id,
                    'percentage': tax_line.percentage,
                    'base_amount': accreditation.original_amount,
                }
                # Calculate amount based on percentage
                if tax_line.percentage and accreditation.original_amount:
                    deduction_vals['amount'] = accreditation.original_amount * (tax_line.percentage / 100)
                
                deduction = self.env['card.tax.deduction'].create(deduction_vals)
                created_deductions |= deduction
            
            processed_count += 1
        
        # Return appropriate action based on operation type
        if self.is_bulk_operation:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Tax Template Applied'),
                    'message': _('Tax template "%s" successfully applied to %d accreditation(s).') % (
                        self.template_id.name, processed_count
                    ),
                    'type': 'success',
                    'sticky': False,
                }
            }
        else:
            # Return action to show the accreditation with new deductions
            return {
                'type': 'ir.actions.act_window',
                'name': _('Accreditation with Applied Deductions'),
                'res_model': 'card.accreditation',
                'res_id': accreditations.id,
                'view_mode': 'form',
                'target': 'current',
            }