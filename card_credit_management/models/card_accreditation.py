# © 2025 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CardAccreditation(models.Model):
    _name = 'card.accreditation'
    _description = 'Credit Card Accreditation Tracking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'collection_date desc, id desc'
    _rec_name = 'display_name'

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )
    
    payment_id = fields.Many2one(
        'account.payment',
        string='Payment',
        required=True,
        ondelete='cascade'
    )
    
    batch_transfer_id = fields.Many2one(
        'card.batch.transfer',
        string='Batch Transfer',
        help='Batch transfer that includes this accreditation',
        ondelete='set null'
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True
    )
    
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        domain=[('is_credit_card', '=', True)]
    )
    
    card_plan_id = fields.Many2one(
        'card.plan',
        string='Card Plan',
        required=True
    )
    
    batch_number = fields.Char(
        string='Batch Number',
        required=True,
        help='Credit card batch number (e.g., Lote 047)'
    )
    
    coupon_number = fields.Char(
        string='Coupon Number',
        required=True,
        help='Credit card coupon number'
    )
    
    collection_date = fields.Date(
        string='Collection Date',
        required=True,
        help='Date when the payment was collected'
    )
    
    original_amount = fields.Monetary(
        string='Original Amount',
        required=True,
        currency_field='currency_id',
        help='Original payment amount'
    )
    
    fee = fields.Monetary(
        string='Card Processing Fee',
        currency_field='currency_id',
        help='Fee charged by the credit card processor (can be manually edited or calculated from plan)',
        default=0.0
    )
    
    financial_cost = fields.Monetary(
        string='Financial Cost (Installments)',
        currency_field='currency_id',
        help='Financial cost for installment payments',
        default=0.0,
        tracking=True
    )
    
    fee_move_id = fields.Many2one(
        'account.move',
        string='Fee Journal Entry',
        readonly=True,
        help='Journal entry created for the processing fee expense'
    )
    
    fee_invoiced = fields.Boolean(
        string='Fee Invoiced',
        default=False,
        help='True if the fee has been included in a vendor invoice'
    )
    
    financial_cost_invoiced = fields.Boolean(
        string='Financial Cost Invoiced',
        default=False,
        help='True if the financial cost has been included in a vendor invoice'
    )
    
    estimated_accreditation_date = fields.Date(
        string='Estimated Accreditation Date',
        help='Calculated date when payment should be credited'
    )
    
    estimated_liquidation_amount = fields.Monetary(
        string='Estimated Liquidation Amount',
        currency_field='currency_id',
        compute='_compute_estimated_liquidation_amount',
        store=True,
        help='Estimated amount after fees, financial costs and tax deductions'
    )
    
    actual_accreditation_date = fields.Date(
        string='Actual Accreditation Date',
        help='Actual date when payment was credited'
    )
    
    actual_liquidation_amount = fields.Monetary(
        string='Actual Liquidation Amount',
        currency_field='currency_id',
        compute='_compute_actual_liquidation_amount',
        store=True,
        help='Actual amount credited after fees, financial costs and tax deductions'
    )
    
    # Deducciones de impuestos
    tax_deduction_ids = fields.One2many(
        'card.tax.deduction',
        'accreditation_id',
        string='Tax Deductions'
    )
    
    total_tax_deductions = fields.Monetary(
        string='Total Tax Deductions',
        compute='_compute_total_tax_deductions',
        store=True,
        currency_field='currency_id'
    )
    
    estimated_amount = fields.Monetary(
        string='Estimated Net Amount',
        compute='_compute_estimated_amount',
        store=True,
        currency_field='currency_id',
        help='Estimated amount after fees and tax deductions'
    )
    
    net_amount = fields.Monetary(
        string='Final Net Amount',
        compute='_compute_net_amount',
        store=True,
        currency_field='currency_id',
        help='Final net amount: Original Amount - Card Processing Fee - Total Tax Deductions'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('credited', 'Credited'),
        ('reconciled', 'Reconciled'),
        ('reversed', 'Reversed'),
    ], string='Status', default='pending', tracking=True)
    
    bank_statement_line_id = fields.Many2one(
        'account.bank.statement.line',
        string='Bank Statement Line',
        help='Related bank statement line after reconciliation'
    )
    
    notes = fields.Text(
        string='Notes',
        help='Additional notes or observations'
    )
    
    movement_type = fields.Selection([
        ('sale', 'Sale'),
        ('refund', 'Refund'),
        ('adjustment', 'Adjustment'),
    ], string='Movement Type', default='sale')

    @api.depends('partner_id', 'journal_id', 'batch_number', 'coupon_number')
    def _compute_display_name(self):
        for record in self:
            parts = []
            if record.partner_id:
                parts.append(record.partner_id.name)
            if record.journal_id:
                parts.append(record.journal_id.name)
            if record.batch_number:
                parts.append(f"Lote {record.batch_number}")
            if record.coupon_number:
                parts.append(f"Cupón {record.coupon_number}")
            
            record.display_name = ' - '.join(parts) if parts else _('Card Accreditation')

    @api.onchange('card_plan_id', 'original_amount')
    def _onchange_fee_calculation(self):
        """Auto-calculate fee and financial cost when plan or amount changes for new records"""
        # Only auto-calculate for new records or when explicitly requested
        if self.card_plan_id and self.original_amount and not self._origin:
            # This is a new record, auto-calculate the fee
            fee_amount = self.original_amount * (self.card_plan_id.fee_percentage / 100)
            self.fee = fee_amount
            
            # Auto-calculate the financial cost
            financial_cost_amount = self.original_amount * (self.card_plan_id.financial_cost_percentage / 100)
            self.financial_cost = financial_cost_amount
    
    def calculate_fee_from_plan(self):
        """Method to recalculate fee and financial cost from plan (can be called manually)"""
        for record in self:
            if record.card_plan_id and record.original_amount:
                fee_amount = record.original_amount * (record.card_plan_id.fee_percentage / 100)
                record.fee = fee_amount
                
                financial_cost_amount = record.original_amount * (record.card_plan_id.financial_cost_percentage / 100)
                record.financial_cost = financial_cost_amount
            else:
                record.fee = 0.0
                record.financial_cost = 0.0

    def action_mark_credited(self):
        """Marca la acreditación como acreditada y postea automáticamente las retenciones"""
        for record in self:
            record.state = 'credited'
            # NOTE: actual_accreditation_date debe ser establecida por el batch transfer
            # no automáticamente al marcar como credited
            
            # NOTE: Fee and financial cost expenses are handled through vendor invoices,
            # not automatic journal entries. Only tax deductions create automatic entries.
            
            # Auto-post all confirmed tax deductions
            record._auto_post_tax_deductions()

    def action_reverse_coupon(self):
        """Reverse the accreditation (mark as rejected by card company)"""
        for record in self:
            if record.state not in ('credited', 'reconciled'):
                raise UserError("Only credited or reconciled accreditations can be reversed.")
            
            if not record.batch_transfer_id:
                raise UserError("Cannot reverse an accreditation that is not part of a batch transfer.")
            
            # Create reversal accreditation with negative amounts
            reversal_vals = {
                'payment_id': record.payment_id.id,
                'partner_id': record.partner_id.id,
                'journal_id': record.journal_id.id,
                'card_plan_id': record.card_plan_id.id,
                'movement_type': record.movement_type,
                'collection_date': record.collection_date,
                'batch_number': record.batch_number,
                'coupon_number': f"{record.coupon_number}-REV",
                'original_amount': -record.original_amount,
                'estimated_liquidation_amount': -record.estimated_liquidation_amount,
                'estimated_accreditation_date': record.estimated_accreditation_date,
                'actual_accreditation_date': fields.Date.today(),
                'actual_liquidation_amount': -record.actual_liquidation_amount,
                'fee': -record.fee if record.fee else 0,
                'net_amount': -record.net_amount,
                'batch_transfer_id': record.batch_transfer_id.id,
                'state': 'reversed',
                'notes': f"Reversal of {record.display_name} - Rejected by card company",
            }
            
            reversal = self.env['card.accreditation'].create(reversal_vals)
            
            # Copy tax deductions with negative amounts
            for deduction in record.tax_deduction_ids:
                deduction.copy({
                    'accreditation_id': reversal.id,
                    'amount': -deduction.amount,
                    'base_amount': -deduction.base_amount,
                    'state': 'posted',
                    'date_applied': fields.Date.today(),
                })
            
            # NOTE: Fee and financial cost expenses are handled through vendor invoices,
            # not automatic journal entries reversal. Only tax deductions need reversal entries.
            
            # Add tracking message
            try:
                record.message_post(
                    body=_("Coupon reversed due to card company rejection. Reversal created: %s") % reversal.display_name
                )
                reversal.message_post(
                    body=_("Reversal of %s - Rejected by card company") % record.display_name
                )
            except AttributeError:
                pass

    def action_create_vendor_invoice(self):
        """Create vendor invoice for card processing fees"""
        self.ensure_one()
        
        if not self.card_plan_id:
            raise UserError("No card plan configured for this accreditation.")
        
        if not self.fee or self.fee <= 0:
            raise UserError("No fee to invoice for this accreditation.")
        
        # TODO: Implement vendor invoice creation logic
        # This method will be expanded to create the actual invoice
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Invoice Creation'),
                'message': _('Invoice creation functionality will be implemented in the next phase.'),
                'type': 'info',
            }
        }

    # NOTE: Método deshabilitado - el estado 'reconciled' se logra automáticamente 
    # a través de la conciliación bancaria del batch transfer
    # def action_mark_reconciled(self):
    #     """Marca la acreditación como conciliada"""
    #     for record in self:
    #         record.state = 'reconciled'

    def action_open_payment(self):
        """Abre el pago relacionado"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'res_id': self.payment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_bank_statement_line(self):
        """Abre la línea de extracto bancario relacionada"""
        self.ensure_one()
        if not self.bank_statement_line_id:
            return
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.bank.statement.line',
            'res_id': self.bank_statement_line_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_batch_transfer(self):
        """Abre el batch transfer relacionado"""
        self.ensure_one()
        if not self.batch_transfer_id:
            return
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'card.batch.transfer',
            'res_id': self.batch_transfer_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_related_moves(self):
        """Muestra todos los asientos contables relacionados al cupón"""
        self.ensure_one()
        
        # Recopilar todos los moves relacionados
        move_ids = []
        
        # Move del pago original
        if self.payment_id and self.payment_id.move_id:
            move_ids.append(self.payment_id.move_id.id)
        
        # Move del fee expense
        if self.fee_move_id:
            move_ids.append(self.fee_move_id.id)
        
        # Moves de las tax deductions
        for deduction in self.tax_deduction_ids:
            if deduction.move_line_id and deduction.move_line_id.move_id:
                move_ids.append(deduction.move_line_id.move_id.id)
        
        # Moves del batch transfer si existe
        if self.batch_transfer_id and self.batch_transfer_id.move_id:
            move_ids.append(self.batch_transfer_id.move_id.id)
        
        # Eliminar duplicados
        move_ids = list(set(move_ids))
        
        if not move_ids:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('No Accounting Entries'),
                    'message': _('No accounting entries found for this accreditation.'),
                    'type': 'info',
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Related Accounting Entries'),
            'res_model': 'account.move',
            'domain': [('id', 'in', move_ids)],
            'view_mode': 'list,form',
            'target': 'current',
            'context': {
                'search_default_posted': 1,
            }
        }

    @api.depends('tax_deduction_ids.amount')
    def _compute_total_tax_deductions(self):
        """Calcula el total de deducciones de impuestos"""
        for record in self:
            record.total_tax_deductions = sum(record.tax_deduction_ids.mapped('amount'))

    @api.depends('original_amount', 'fee', 'financial_cost', 'total_tax_deductions')
    def _compute_estimated_amount(self):
        """Calcula el monto estimado neto: Original Amount - Fee - Financial Cost - Total Tax Deductions"""
        for record in self:
            record.estimated_amount = record.original_amount - record.fee - record.financial_cost - record.total_tax_deductions

    @api.depends('original_amount', 'fee', 'financial_cost', 'total_tax_deductions')
    def _compute_net_amount(self):
        """Calcula el monto neto final: Original Amount - Card Processing Fee - Financial Cost - Total Tax Deductions"""
        for record in self:
            record.net_amount = record.original_amount - record.fee - record.financial_cost - record.total_tax_deductions

    @api.depends('original_amount', 'fee', 'financial_cost', 'total_tax_deductions')
    def _compute_estimated_liquidation_amount(self):
        """Calcula el monto estimado de liquidación: Original Amount - Fee - Financial Cost - Total Tax Deductions"""
        for record in self:
            record.estimated_liquidation_amount = record.original_amount - record.fee - record.financial_cost - record.total_tax_deductions

    @api.depends('original_amount', 'fee', 'financial_cost', 'total_tax_deductions')
    def _compute_actual_liquidation_amount(self):
        """Calcula el monto actual de liquidación: Original Amount - Fee - Financial Cost - Total Tax Deductions"""
        for record in self:
            record.actual_liquidation_amount = record.original_amount - record.fee - record.financial_cost - record.total_tax_deductions

    def action_apply_all_tax_deductions(self):
        """Aplica todas las deducciones de impuestos confirmadas"""
        self.ensure_one()
        
        confirmed_deductions = self.tax_deduction_ids.filtered(lambda d: d.state == 'confirmed')
        if confirmed_deductions:
            confirmed_deductions.action_post()

    def _auto_post_tax_deductions(self):
        """Postea automáticamente todas las retenciones de impuestos cuando el cupón se acredita"""
        self.ensure_one()
        
        # Buscar todas las retenciones que están confirmadas pero no posteadas
        unposted_deductions = self.tax_deduction_ids.filtered(lambda d: d.state == 'confirmed')
        
        if unposted_deductions:
            try:
                # Postear todas las retenciones confirmadas
                unposted_deductions.action_post()
                
                # Agregar mensaje de seguimiento
                self.message_post(
                    body=_("Auto-posted %d tax deduction(s): %s") % (
                        len(unposted_deductions),
                        ', '.join(unposted_deductions.mapped('name'))
                    )
                )
                
            except Exception as e:
                # Si hay algún error, registrarlo pero no detener el proceso
                self.message_post(
                    body=_("Warning: Could not auto-post tax deductions: %s") % str(e)
                )
        
        # También confirmar automáticamente las retenciones en borrador
        draft_deductions = self.tax_deduction_ids.filtered(lambda d: d.state == 'draft')
        if draft_deductions:
            try:
                # Confirmar las retenciones en borrador
                draft_deductions.action_confirm()
                
                # Luego postearlas
                draft_deductions.action_post()
                
                # Agregar mensaje de seguimiento
                self.message_post(
                    body=_("Auto-confirmed and posted %d tax deduction(s): %s") % (
                        len(draft_deductions),
                        ', '.join(draft_deductions.mapped('name'))
                    )
                )
                
            except Exception as e:
                # Si hay algún error, registrarlo pero no detener el proceso
                self.message_post(
                    body=_("Warning: Could not auto-confirm and post tax deductions: %s") % str(e)
                )

    def _sync_payment_to_draft(self):
        """Synchronize payment state when accreditation goes to draft"""
        self.ensure_one()
        
        if not self.payment_id:
            return
        
        # Check if this is the only accreditation for this payment
        payment_accreditations = self.env['card.accreditation'].search([
            ('payment_id', '=', self.payment_id.id)
        ])
        
        # Only sync if this is the only accreditation or all accreditations are in draft
        all_draft = all(acc.state == 'draft' for acc in payment_accreditations)
        
        if all_draft and self.payment_id.state != 'draft':
            try:
                # Try to set payment to draft
                self.payment_id.action_draft()
            except UserError:
                # If it fails due to batch transfer restrictions, that's expected
                pass

    @api.model
    def search_by_batch_coupon(self, batch_number, coupon_number=None):
        """Busca acreditaciones por número de lote y opcionalmente cupón"""
        domain = [('batch_number', '=', batch_number)]
        if coupon_number:
            domain.append(('coupon_number', '=', coupon_number))
        
        return self.search(domain)

    def action_create_payment_batch(self):
        """Crear pago para acreditar cupón individual"""
        self.ensure_one()
        
        if self.state != 'pending':
            raise UserError(_("Only pending accreditations can be processed into payments."))
        
        # Crear pago individual
        payment_vals = {
            'partner_id': self.partner_id.id,
            'amount': self.net_amount or self.estimated_liquidation_amount,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'journal_id': self.journal_id.id,
            'date': self.actual_accreditation_date or self.estimated_accreditation_date,
            'payment_reference': f'Card Payment - Batch {self.batch_number} - Coupon {self.coupon_number}',
            'card_batch_number': self.batch_number,
            'card_coupon_number': self.coupon_number,
            'card_plan_id': self.card_plan_id.id,
        }
        
        payment = self.env['account.payment'].create(payment_vals)
        
        # Marcar como acreditado
        self.write({
            'state': 'credited',
            'actual_accreditation_date': fields.Date.today(),
            'actual_liquidation_amount': payment.amount,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Card Payment'),
            'res_model': 'account.payment',
            'res_id': payment.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_tax_deductions(self):
        """Abrir vista de deducciones de impuestos"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tax Deductions'),
            'res_model': 'card.tax.deduction',
            'view_mode': 'list,form',
            'domain': [('accreditation_id', '=', self.id)],
            'context': {
                'default_accreditation_id': self.id,
                'default_base_amount': self.original_amount,
            },
            'target': 'current',
        }

    def action_bulk_create_payment_batch(self):
        """Crear pagos para múltiples acreditaciones seleccionadas"""
        pending_accreditations = self.filtered(lambda a: a.state == 'pending')
        
        if not pending_accreditations:
            raise UserError(_("No pending accreditations found to process."))
        
        # Crear pagos individuales
        created_payments = []
        for accreditation in pending_accreditations:
            # Crear pago individual
            payment_vals = {
                'partner_id': accreditation.partner_id.id,
                'amount': accreditation.net_amount or accreditation.estimated_liquidation_amount,
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'journal_id': accreditation.journal_id.id,
                'date': accreditation.actual_accreditation_date or accreditation.estimated_accreditation_date,
                'payment_reference': f'Card Payment - Batch {accreditation.batch_number} - Coupon {accreditation.coupon_number}',
                'card_batch_number': accreditation.batch_number,
                'card_coupon_number': accreditation.coupon_number,
                'card_plan_id': accreditation.card_plan_id.id,
            }
            
            payment = self.env['account.payment'].create(payment_vals)
            created_payments.append(payment.id)
            
            # Marcar como acreditado
            accreditation.write({
                'state': 'credited',
                'actual_accreditation_date': fields.Date.today(),
                'actual_liquidation_amount': payment.amount,
            })
        
        if len(created_payments) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Card Payment'),
                'res_model': 'account.payment',
                'res_id': created_payments[0],
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Card Payments'),
                'res_model': 'account.payment',
                'view_mode': 'list,form',
                'domain': [('id', 'in', created_payments)],
                'target': 'current',
            }
    
    def action_apply_tax_template(self):
        """Show wizard to select and apply tax template"""
        self.ensure_one()
        
        templates = self.env['card.tax.deduction.template'].search([
            ('active', '=', True),
            ('company_id', '=', self.company_id.id)
        ])
        
        if not templates:
            raise UserError("No active tax deduction templates found. Please create templates first.")
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Apply Tax Template'),
            'res_model': 'card.tax.template.wizard',
            'view_mode': 'form',
            'context': {
                'default_accreditation_id': self.id,
            },
            'target': 'new',
        }
    
    def action_create_batch_transfer(self):
        """Create batch transfer for individual accreditation"""
        self.ensure_one()
        
        if self.state != 'pending':
            raise UserError("Only pending accreditations can be included in batch transfers.")
        
        if not self.journal_id.final_bank_journal_id:
            raise UserError(
                f"No destination bank journal configured for {self.journal_id.name}. "
                "Please configure the 'Final Bank Journal' in the credit card journal settings."
            )
        
        # Create wizard to select more accreditations for the batch
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Batch Transfer'),
            'res_model': 'card.batch.transfer.wizard',
            'view_mode': 'form',
            'context': {
                'default_source_journal_id': self.journal_id.id,
                'default_destination_journal_id': self.journal_id.final_bank_journal_id.id,
                'default_accreditation_ids': [(6, 0, [self.id])],
            },
            'target': 'new',
        }
    
    def action_bulk_create_batch_transfer(self):
        """Create batch transfer for multiple selected accreditations"""
        if not self:
            raise UserError("No accreditations selected.")
        
        # Validate all accreditations
        pending_accreditations = self.filtered(lambda a: a.state == 'pending')
        if not pending_accreditations:
            raise UserError("No pending accreditations found in selection.")
        
        if len(pending_accreditations) != len(self):
            raise UserError("All selected accreditations must be in pending state.")
        
        # Check that all accreditations are from the same journal
        journals = pending_accreditations.mapped('journal_id')
        if len(journals) > 1:
            raise UserError("All selected accreditations must be from the same credit card journal.")
        
        journal = journals[0]
        if not journal.final_bank_journal_id:
            raise UserError(
                f"No destination bank journal configured for {journal.name}. "
                "Please configure the 'Final Bank Journal' in the credit card journal settings."
            )
        
        # Create wizard with selected accreditations
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Batch Transfer'),
            'res_model': 'card.batch.transfer.wizard',
            'view_mode': 'form',
            'context': {
                'default_source_journal_id': journal.id,
                'default_destination_journal_id': journal.final_bank_journal_id.id,
                'default_accreditation_ids': [(6, 0, pending_accreditations.ids)],
            },
            'target': 'new',
        }

    def action_bulk_apply_tax_template(self):
        """Apply tax template to multiple selected accreditations"""
        # Filter only accreditations that can have tax templates applied
        valid_accreditations = self.filtered(lambda r: r.state in ('pending', 'credited'))
        
        if not valid_accreditations:
            raise UserError("Please select at least one accreditation that can have tax deductions applied (pending or credited).")
        
        # Open wizard to select tax template
        return {
            'type': 'ir.actions.act_window',
            'name': _('Apply Tax Template to Selected Accreditations'),
            'res_model': 'card.tax.template.wizard',
            'view_mode': 'form',
            'context': {
                'default_accreditation_ids': [(6, 0, valid_accreditations.ids)],
                'bulk_operation': True,
            },
            'target': 'new',
        }

    def action_add_to_batch(self):
        """Add selected accreditations to an existing batch transfer or create new one"""
        # Filter only pending accreditations that are not already in a batch
        valid_accreditations = self.filtered(lambda r: r.state == 'pending' and not r.batch_transfer_id)
        
        if not valid_accreditations:
            raise UserError("Please select at least one pending accreditation that is not already in a batch transfer.")
        
        # Check if all accreditations are from the same journal
        journals = valid_accreditations.mapped('journal_id')
        if len(journals) > 1:
            raise UserError("All selected accreditations must be from the same credit card journal.")
        
        source_journal = journals[0]
        
        # Verify journal has destination bank configured
        if not source_journal.final_bank_journal_id:
            raise UserError(
                f"No destination bank journal configured for {source_journal.name}. "
                "Please configure the 'Final Bank Journal' in the credit card journal settings."
            )
        
        # Get available batch transfers (only in draft or confirmed state) for the same journal
        available_batches = self.env['card.batch.transfer'].search([
            ('state', 'in', ['draft', 'confirmed']),
            ('source_journal_id', '=', source_journal.id)
        ])
        
        if available_batches:
            # Open wizard to select batch transfer
            return {
                'type': 'ir.actions.act_window',
                'name': _('Add to Batch Transfer'),
                'res_model': 'card.add.to.batch.wizard',
                'view_mode': 'form',
                'context': {
                    'default_accreditation_ids': [(6, 0, valid_accreditations.ids)],
                },
                'target': 'new',
            }
        else:
            # No available batches, create a new one automatically
            batch_transfer = self.env['card.batch.transfer'].create({
                'transfer_date': fields.Date.today(),
                'source_journal_id': source_journal.id,
                'destination_journal_id': source_journal.final_bank_journal_id.id,
                'notes': f'Auto-created batch for {len(valid_accreditations)} accreditations',
            })
            
            # Add accreditations to the new batch and mark as credited
            valid_accreditations.write({
                'batch_transfer_id': batch_transfer.id,
                'state': 'credited',
                'actual_accreditation_date': fields.Date.today()
            })
            
            # Auto-post tax deductions and create fee expenses
            for accreditation in valid_accreditations:
                # Auto-post all confirmed tax deductions
                confirmed_deductions = accreditation.tax_deduction_ids.filtered(lambda d: d.state == 'confirmed')
                if confirmed_deductions:
                    confirmed_deductions.action_post()
                
                # NOTE: Fee and financial cost expenses are handled through vendor invoices,
                # not automatic journal entries. Only tax deductions create automatic entries.
            
            # Confirm the batch automatically
            batch_transfer.action_confirm()
            
            # Return to the created batch transfer
            return {
                'type': 'ir.actions.act_window',
                'name': _('Batch Transfer'),
                'res_model': 'card.batch.transfer',
                'res_id': batch_transfer.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def action_remove_from_batch(self):
        """Remove accreditation from batch transfer and return to pending state"""
        self.ensure_one()
        
        if not self.batch_transfer_id:
            raise UserError("This accreditation is not part of any batch transfer.")
        
        if self.batch_transfer_id.state != 'draft':
            raise UserError("Can only remove accreditations from batch transfers in draft state.")
        
        batch_transfer = self.batch_transfer_id
        
        # Remove from batch and return to pending
        self.write({
            'batch_transfer_id': False,
            'state': 'pending',
            'actual_accreditation_date': False,
            'actual_liquidation_amount': False,
            'net_amount': 0.0,
        })
        
        # Recalculate batch transfer totals
        batch_transfer._compute_total_amount()
        batch_transfer._compute_final_transfer_amount()
        
        # Log the removal
        self.message_post(
            body=f"Removed from batch transfer {batch_transfer.name}",
            message_type='notification'
        )
        
        batch_transfer.message_post(
            body=f"Accreditation {self.display_name} was removed from this batch",
            message_type='notification'
        )
        
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_reset_to_pending(self):
        """Reset accreditation back to pending status"""
        for accreditation in self:
            if accreditation.state == 'pending':
                raise UserError("Accreditation is already in pending status.")
            
            if accreditation.batch_transfer_id and accreditation.batch_transfer_id.state in ('confirmed', 'transferred'):
                raise UserError(
                    f"Cannot reset accreditation that is part of a confirmed or transferred batch transfer "
                    f"({accreditation.batch_transfer_id.name}). Please cancel the batch transfer first."
                )
            
            # Remove from any batch transfer
            if accreditation.batch_transfer_id:
                accreditation.batch_transfer_id = False
            
            # Reverse fee expense if exists
            if accreditation.fee_move_id:
                if accreditation.fee_move_id.state == 'draft':
                    accreditation.fee_move_id.unlink()
                else:
                    # Create reversal entry
                    reversal = accreditation.fee_move_id._reverse_moves([{
                        'ref': f'Reversal of fee for {accreditation.display_name} - Reset to pending',
                        'date': fields.Date.today(),
                    }])
                    reversal.action_post()
                accreditation.fee_move_id = False
            
            # Reset to pending state
            accreditation.write({
                'state': 'pending',
                'actual_accreditation_date': False,
                'actual_liquidation_amount': 0.0,
            })
            
            # Add tracking message (optional, in case mail.thread is not available)
            try:
                accreditation.message_post(
                    body=_("Accreditation reset to pending status by %s") % self.env.user.name
                )
            except AttributeError:
                # Silently continue if message_post is not available
                pass

    def action_set_to_draft(self):
        """Set accreditation to draft state"""
        for accreditation in self:
            if accreditation.batch_transfer_id and accreditation.batch_transfer_id.state != 'draft':
                raise UserError(_(
                    "Cannot set accreditation to draft because it's included in batch transfer %s "
                    "which is not in draft state. Please set the batch transfer to draft first."
                ) % accreditation.batch_transfer_id.name)
            
            accreditation.write({'state': 'draft'})

    @api.model
    def create(self, vals):
        """Override create to handle fee expense generation"""
        record = super().create(vals)
        # NOTE: Fee and financial cost expenses are handled through vendor invoices,
        # not automatic journal entries. Only tax deductions create automatic entries.
        return record

    def write(self, vals):
        """Override write to handle fee expense generation and tax deduction auto-posting"""
        # Store old fee values before writing
        old_fees = {}
        if 'fee' in vals:
            for record in self:
                old_fees[record.id] = record.fee
        
        # Store old state values to detect state changes
        old_states = {}
        if 'state' in vals:
            for record in self:
                old_states[record.id] = record.state
        
        result = super().write(vals)
        
        # Handle fee changes only if fee actually changed
        if 'fee' in vals:
            for record in self:
                old_fee = old_fees.get(record.id, 0)
                new_fee = vals.get('fee', 0)
                if old_fee != new_fee:
                    record._handle_fee_change(new_fee)
        
        # Handle state changes to 'credited' - auto-post tax deductions
        if 'state' in vals and vals.get('state') == 'credited':
            for record in self:
                old_state = old_states.get(record.id)
                # Only process if state actually changed to 'credited'
                if old_state != 'credited':
                    record._auto_post_tax_deductions()
        
        # Handle state changes to synchronize with payment state
        if 'state' in vals:
            for record in self:
                old_state = old_states.get(record.id)
                new_state = vals.get('state')
                
                # If accreditation moves to draft, try to set payment to draft
                if new_state == 'draft' and old_state != 'draft':
                    record._sync_payment_to_draft()
        
        return result

    def _handle_fee_change(self, new_fee):
        """Handle fee changes by creating/updating fee expense"""
        self.ensure_one()
        
        # Skip if accreditation is not in credited state
        if self.state != 'credited':
            return
        
        # If there's an existing fee entry, reverse it first
        if self.fee_move_id:
            if self.fee_move_id.state == 'draft':
                self.fee_move_id.unlink()
            else:
                # Create reversal entry
                reversal = self.fee_move_id._reverse_moves([{
                    'ref': f'Reversal of fee for {self.display_name}',
                    'date': fields.Date.today(),
                }])
                reversal.action_post()
            self.fee_move_id = False
        
        # NOTE: Fee and financial cost expenses are handled through vendor invoices,
        # not automatic journal entries. Only tax deductions create automatic entries.

    def _create_fee_expense(self):
        """
        DEPRECATED: Create accounting entry for card processing fee using card plan accounts
        
        NOTE: This method is deprecated as fee and financial cost expenses are now handled 
        through vendor invoices, not automatic journal entries. Only tax deductions 
        should create automatic journal entries.
        
        This method is kept for backward compatibility but should not be called automatically.
        """
        return  # Early return - method disabled
        
        # Original implementation commented out:
        # if not self.fee or self.fee <= 0:
        #     return
        #     
        # if not self.card_plan_id:
        #     raise UserError(_("Card plan is required to create fee expense entries"))
        # ... rest of implementation
        
        # Get accounts from card plan configuration
        fee_account = self.card_plan_id.fee_account_id
        financial_cost_account = self.card_plan_id.financial_cost_account_id
        vat_account = self.card_plan_id.vat_account_id
        gross_income_account = self.card_plan_id.gross_income_account_id
        
        if not fee_account:
            raise UserError(_("Fee account not configured in card plan: %s") % self.card_plan_id.name)
        
        # Calculate fee components based on card plan configuration
        base_fee = self.fee
        vat_amount = 0.0
        gross_income_amount = 0.0
        financial_cost = 0.0
        
        # If VAT account is configured, calculate VAT (typically 21% in Argentina)
        if vat_account and hasattr(self.card_plan_id, 'vat_percentage'):
            vat_amount = base_fee * (self.card_plan_id.vat_percentage / 100)
        
        # If Gross Income account is configured, calculate gross income tax
        if gross_income_account and hasattr(self.card_plan_id, 'gross_income_percentage'):
            gross_income_amount = base_fee * (self.card_plan_id.gross_income_percentage / 100)
        
        # If Financial Cost account is configured, use it for additional costs
        if financial_cost_account and hasattr(self.card_plan_id, 'financial_cost_percentage'):
            financial_cost = base_fee * (self.card_plan_id.financial_cost_percentage / 100)
        
        # Get credit card account (from journal or card plan)
        credit_card_account = self.journal_id.default_account_id
        if not credit_card_account and hasattr(self.card_plan_id, 'credit_card_account_id'):
            credit_card_account = self.card_plan_id.credit_card_account_id
        
        if not credit_card_account:
            raise UserError(_("No default account configured for journal %s") % self.journal_id.name)
        
        # Build journal entry lines
        line_ids = []
        
        # Main fee expense (debit)
        line_ids.append((0, 0, {
            'name': f'Card processing fee - {self.partner_id.name}',
            'account_id': fee_account.id,
            'debit': base_fee,
            'credit': 0.0,
            'partner_id': self.partner_id.id,
        }))
        
        # VAT if configured (debit)
        if vat_amount > 0 and vat_account:
            line_ids.append((0, 0, {
                'name': f'VAT on card processing fee - {self.partner_id.name}',
                'account_id': vat_account.id,
                'debit': vat_amount,
                'credit': 0.0,
                'partner_id': self.partner_id.id,
            }))
        
        # Gross Income if configured (debit)
        if gross_income_amount > 0 and gross_income_account:
            line_ids.append((0, 0, {
                'name': f'Gross Income tax on card processing fee - {self.partner_id.name}',
                'account_id': gross_income_account.id,
                'debit': gross_income_amount,
                'credit': 0.0,
                'partner_id': self.partner_id.id,
            }))
        
        # Financial Cost if configured (debit)
        if financial_cost > 0 and financial_cost_account:
            line_ids.append((0, 0, {
                'name': f'Financial cost on card processing fee - {self.partner_id.name}',
                'account_id': financial_cost_account.id,
                'debit': financial_cost,
                'credit': 0.0,
                'partner_id': self.partner_id.id,
            }))
        
        # Credit card account (credit) - total amount
        total_amount = base_fee + vat_amount + gross_income_amount + financial_cost
        line_ids.append((0, 0, {
            'name': f'Card processing fee payment - {self.partner_id.name}',
            'account_id': credit_card_account.id,
            'debit': 0.0,
            'credit': total_amount,
            'partner_id': self.partner_id.id,
        }))
        
        # Create journal entry
        move_vals = {
            'journal_id': self.journal_id.id,
            'date': self.collection_date or fields.Date.today(),
            'ref': f'Card processing fee - {self.display_name}',
            'line_ids': line_ids,
        }
        
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        
        self.fee_move_id = move.id
        
        # Add tracking message
        self.message_post(
            body=_("Card processing fee expense created: %s") % move.name
        )