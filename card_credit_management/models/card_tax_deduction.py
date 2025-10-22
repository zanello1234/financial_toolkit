# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class CardTaxDeduction(models.Model):
    _name = 'card.tax.deduction'
    _description = 'Credit Card Tax Deduction'
    _order = 'accreditation_id, sequence, id'

    # Relaciones
    accreditation_id = fields.Many2one(
        'card.accreditation', 
        string='Accreditation',
        required=True,
        ondelete='cascade'
    )
    
    tax_account_id = fields.Many2one(
        'account.account',
        string='Tax Account',
        required=True,
        domain="[('account_type', 'in', ['asset_current', 'liability_current'])]",
        help="Account for tax withholding/deduction"
    )
    
    # Campos básicos
    name = fields.Char(
        string='Description',
        required=True,
        help="Description of the tax deduction"
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    amount = fields.Monetary(
        string='Deduction Amount',
        required=True,
        currency_field='currency_id'
    )
    
    percentage = fields.Float(
        string='Percentage (%)',
        digits=(5, 2),
        help="Percentage of deduction over base amount"
    )
    
    base_amount = fields.Monetary(
        string='Base Amount',
        currency_field='currency_id',
        help="Base amount for percentage calculation"
    )
    
    # Estado y fechas
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('posted', 'Posted')
    ], string='State', default='draft')
    
    date_applied = fields.Date(
        string='Date Applied',
        help="Date when the deduction was applied"
    )
    
    # Campos relacionados
    currency_id = fields.Many2one(
        related='accreditation_id.currency_id',
        store=True
    )
    
    company_id = fields.Many2one(
        related='accreditation_id.company_id',
        store=True
    )
    
    # Contabilidad
    move_line_id = fields.Many2one(
        'account.move.line',
        string='Journal Item',
        readonly=True,
        help="Journal item created for this deduction"
    )
    
    # Campos computados
    applied = fields.Boolean(
        string='Applied',
        compute='_compute_applied',
        store=True
    )
    
    @api.depends('state', 'move_line_id')
    def _compute_applied(self):
        for deduction in self:
            deduction.applied = deduction.state == 'posted' and bool(deduction.move_line_id)
    
    @api.onchange('percentage', 'base_amount')
    def _onchange_percentage(self):
        """Calcular monto basado en porcentaje"""
        if self.percentage and self.base_amount:
            self.amount = self.base_amount * (self.percentage / 100)
    
    @api.onchange('accreditation_id')
    def _onchange_accreditation_id(self):
        """Establecer monto base cuando cambia la acreditación"""
        if self.accreditation_id:
            self.base_amount = self.accreditation_id.original_amount
    
    @api.constrains('amount')
    def _check_amount(self):
        for deduction in self:
            if deduction.amount <= 0:
                raise ValidationError("Deduction amount must be positive")
            if deduction.accreditation_id and deduction.amount > deduction.accreditation_id.original_amount:
                raise ValidationError("Deduction amount cannot exceed original accreditation amount")
    
    @api.constrains('percentage')
    def _check_percentage(self):
        for deduction in self:
            if deduction.percentage < 0 or deduction.percentage > 100:
                raise ValidationError("Percentage must be between 0 and 100")
    
    def action_confirm(self):
        """Confirmar la deducción"""
        for deduction in self:
            if deduction.state != 'draft':
                raise UserError("Only draft deductions can be confirmed")
            deduction.write({
                'state': 'confirmed',
                'date_applied': fields.Date.today()
            })
    
    def action_post(self):
        """Registrar la deducción contablemente"""
        for deduction in self:
            if deduction.state != 'confirmed':
                raise UserError("Only confirmed deductions can be posted")
            
            try:
                # Crear asiento contable
                move_line = deduction._create_accounting_entry()
                deduction.write({
                    'state': 'posted',
                    'move_line_id': move_line.id,
                    'date_applied': fields.Date.today()
                })
            except Exception as e:
                raise UserError(f"Error creating accounting entry: {str(e)}")
    
    def action_cancel(self):
        """Cancelar la deducción"""
        for deduction in self:
            if deduction.state == 'posted':
                raise UserError("Cannot cancel posted deductions")
            deduction.state = 'draft'
    
    def _create_accounting_entry(self):
        """Crear asiento contable para la deducción"""
        self.ensure_one()
        
        if not self.accreditation_id.payment_id:
            raise UserError("Cannot create accounting entry without associated payment")
        
        payment = self.accreditation_id.payment_id
        
        # Verificar si el pago está confirmado
        if payment.state == 'draft':
            raise UserError(
                "The payment must be confirmed before applying tax deductions. "
                "Please confirm the payment first and then apply the deduction."
            )
        
        # Crear asiento independiente para la deducción
        journal = payment.journal_id
        
        # Obtener la cuenta de pagos desde las líneas de métodos de pago
        outstanding_account = None
        
        # Buscar en las líneas de métodos de pago del diario
        if payment.payment_method_line_id and payment.payment_method_line_id.payment_account_id:
            outstanding_account = payment.payment_method_line_id.payment_account_id
        else:
            # Buscar la primera línea de método de pago con cuenta configurada
            payment_method_lines = journal.inbound_payment_method_line_ids + journal.outbound_payment_method_line_ids
            for line in payment_method_lines:
                if line.payment_account_id:
                    outstanding_account = line.payment_account_id
                    break
        
        # Si no encontramos cuenta en métodos de pago, usar cuenta por defecto del diario
        if not outstanding_account:
            outstanding_account = journal.default_account_id
            
        if not outstanding_account:
            raise UserError(
                f"No payment account configured for journal {journal.name}. "
                "Please configure a payment account in the payment method lines or set a default account."
            )
        
        # Crear nuevo asiento
        move_vals = {
            'ref': f"Tax Deduction: {self.name}",
            'journal_id': journal.id,
            'date': fields.Date.today(),
            'line_ids': [
                # Línea de débito para el impuesto
                (0, 0, {
                    'account_id': self.tax_account_id.id,
                    'name': f"Tax Deduction: {self.name}",
                    'debit': self.amount,
                    'credit': 0.0,
                    'partner_id': payment.partner_id.id,
                }),
                # Línea de crédito para la cuenta de recibos pendientes
                (0, 0, {
                    'account_id': outstanding_account.id,
                    'name': f"Tax Deduction Applied: {self.name}",
                    'debit': 0.0,
                    'credit': self.amount,
                    'partner_id': payment.partner_id.id,
                })
            ]
        }
        
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        
        # Retornar la primera línea (débito)
        return move.line_ids.filtered(lambda l: l.debit > 0)[0]
    
    def unlink(self):
        """Prevenir eliminación de deducciones registradas"""
        for deduction in self:
            if deduction.state == 'posted':
                raise UserError("Cannot delete posted tax deductions")
        return super().unlink()


class CardTaxDeductionTemplate(models.Model):
    _name = 'card.tax.deduction.template'
    _description = 'Credit Card Tax Deduction Template'
    _order = 'sequence, name'

    name = fields.Char(
        string='Template Name',
        required=True
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    tax_line_ids = fields.One2many(
        'card.tax.deduction.template.line',
        'template_id',
        string='Tax Lines',
        help='Multiple tax deductions that can be applied together'
    )
    
    description = fields.Text(
        string='Description'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    
    def action_apply_to_accreditation(self):
        """Show wizard to select accreditation to apply template"""
        self.ensure_one()
        
        # Get available accreditations (not reconciled)
        accreditations = self.env['card.accreditation'].search([
            ('state', '!=', 'reconciled'),
            ('company_id', '=', self.company_id.id)
        ])
        
        if not accreditations:
            raise UserError("No available accreditations found to apply tax deductions.")
        
        # Get active accreditation from context if available
        accreditation_id = self.env.context.get('active_id')
        if accreditation_id and self.env.context.get('active_model') == 'card.accreditation':
            accreditation = self.env['card.accreditation'].browse(accreditation_id)
            if accreditation and accreditation.state != 'reconciled':
                return self._apply_template_to_accreditation(accreditation)
        
        # If no active accreditation or not valid, show selection wizard
        return {
            'type': 'ir.actions.act_window',
            'name': _('Select Accreditation'),
            'res_model': 'card.accreditation',
            'view_mode': 'list',
            'domain': [('id', 'in', accreditations.ids)],
            'context': {
                'template_id': self.id,
                'action_after_select': 'apply_template',
            },
            'target': 'new',
        }
    
    def _apply_template_to_accreditation(self, accreditation):
        """Apply template to specific accreditation"""
        self.ensure_one()
        
        if not self.tax_line_ids:
            raise UserError("No tax lines configured in template")
        
        # Create deductions for each tax line
        created_deductions = self.env['card.tax.deduction']
        for tax_line in self.tax_line_ids:
            deduction_vals = {
                'name': f"{self.name} - {tax_line.name}",
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
        
        # Return action to show created deductions
        return {
            'type': 'ir.actions.act_window',
            'name': 'Created Tax Deductions',
            'res_model': 'card.tax.deduction',
            'domain': [('id', 'in', created_deductions.ids)],
            'view_mode': 'list,form',
            'target': 'current',
        }


class CardTaxDeductionTemplateLine(models.Model):
    _name = 'card.tax.deduction.template.line'
    _description = 'Credit Card Tax Deduction Template Line'
    _order = 'sequence, name'

    template_id = fields.Many2one(
        'card.tax.deduction.template',
        string='Template',
        required=True,
        ondelete='cascade'
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )
    
    name = fields.Char(
        string='Tax Name',
        required=True
    )
    
    tax_account_id = fields.Many2one(
        'account.account',
        string='Tax Account',
        required=True,
        domain="[('account_type', 'in', ['asset_current', 'liability_current'])]"
    )
    
    percentage = fields.Float(
        string='Percentage (%)',
        digits=(5, 2),
        required=True
    )
    
    description = fields.Text(
        string='Description'
    )