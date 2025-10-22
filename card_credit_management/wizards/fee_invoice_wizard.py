from odoo import models, fields, api, _
from odoo.exceptions import UserError


class FeeInvoiceWizard(models.TransientModel):
    _name = 'card.fee.invoice.wizard'
    _description = 'Create Fee Invoice Wizard'

    partner_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        required=True,
        domain="['|', ('is_company', '=', True), ('supplier_rank', '>', 0)]",
        help='Select the credit card processor vendor to invoice'
    )
    
    journal_id = fields.Many2one(
        'account.journal',
        string='Purchase Journal',
        required=True,
        domain=[('type', '=', 'purchase')],
        help='Journal for the vendor invoice'
    )
    
    accreditation_ids = fields.Many2many(
        'card.accreditation',
        string='Selected Accreditations',
        readonly=True,
        help='Accreditations selected for invoicing'
    )
    
    total_fee_amount = fields.Monetary(
        string='Total Fee Amount',
        compute='_compute_total_fee_amount',
        currency_field='currency_id'
    )
    
    total_financial_cost = fields.Monetary(
        string='Total Financial Cost',
        compute='_compute_total_financial_cost',
        currency_field='currency_id'
    )
    
    include_financial_cost = fields.Boolean(
        string='Include Financial Cost in Invoice',
        default=True,
        help='Check to include financial cost of installments in the invoice'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    
    invoice_date = fields.Date(
        string='Invoice Date',
        default=fields.Date.context_today,
        required=True
    )
    
    description = fields.Text(
        string='Invoice Description',
        default='Credit card processing fees'
    )

    @api.depends('accreditation_ids')
    def _compute_total_fee_amount(self):
        for wizard in self:
            wizard.total_fee_amount = sum(wizard.accreditation_ids.mapped('fee'))

    @api.depends('accreditation_ids')
    def _compute_total_financial_cost(self):
        for wizard in self:
            wizard.total_financial_cost = sum(wizard.accreditation_ids.mapped('financial_cost'))

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        
        # Get selected accreditations from context
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            accreditations = self.env['card.accreditation'].browse(active_ids)
            
            # Filter accreditations with fees or financial costs that haven't been invoiced
            valid_accreditations = accreditations.filtered(
                lambda acc: (acc.fee > 0 and not acc.fee_invoiced) or 
                           (acc.financial_cost > 0 and not acc.financial_cost_invoiced)
            )
            
            if not valid_accreditations:
                raise UserError(_('No valid accreditations selected. Please select accreditations with fees or financial costs that have not been invoiced yet.'))
            
            res['accreditation_ids'] = [(6, 0, valid_accreditations.ids)]
            
            # Set default journal (first purchase journal)
            purchase_journal = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
            if purchase_journal:
                res['journal_id'] = purchase_journal.id
        
        return res

    def action_create_invoice(self):
        """Create vendor invoice with selected fee and financial cost lines"""
        self.ensure_one()
        
        if not self.accreditation_ids:
            raise UserError(_('No accreditations selected.'))
        
        # Check if any accreditation is already invoiced
        already_invoiced_fee = self.accreditation_ids.filtered('fee_invoiced')
        already_invoiced_financial = self.accreditation_ids.filtered('financial_cost_invoiced') if self.include_financial_cost else self.env['card.accreditation']
        
        if already_invoiced_fee or already_invoiced_financial:
            msg_parts = []
            if already_invoiced_fee:
                msg_parts.append('fees already invoiced')
            if already_invoiced_financial:
                msg_parts.append('financial costs already invoiced')
            raise UserError(_(
                'Some selected accreditations have %s. Please exclude them or use different accreditations.'
            ) % ' and '.join(msg_parts))
        
        # Create vendor invoice
        invoice_vals = {
            'move_type': 'in_invoice',
            'partner_id': self.partner_id.id,
            'journal_id': self.journal_id.id,
            'invoice_date': self.invoice_date,
            'currency_id': self.currency_id.id,
            'ref': f'Credit Card Processing Costs - {fields.Date.to_string(self.invoice_date)}',
            'narration': self.description,
            'invoice_line_ids': [],
        }
        
        # Create invoice lines for each accreditation
        for accreditation in self.accreditation_ids:
            # Add fee line if fee > 0 and not already invoiced
            if accreditation.fee > 0 and not accreditation.fee_invoiced:
                fee_line_vals = {
                    'name': f'Credit Card Processing Fee - {accreditation.partner_id.name} - {accreditation.collection_date} - Batch: {accreditation.batch_number or "N/A"} - Coupon: {accreditation.coupon_number or "N/A"}',
                    'quantity': 1,
                    'price_unit': accreditation.fee,
                    'account_id': self._get_fee_expense_account(accreditation),
                }
                invoice_vals['invoice_line_ids'].append((0, 0, fee_line_vals))
            
            # Add financial cost line if requested and cost > 0 and not already invoiced
            if (self.include_financial_cost and 
                accreditation.financial_cost > 0 and 
                not accreditation.financial_cost_invoiced):
                
                financial_line_vals = {
                    'name': f'Financial Cost (Installments) - {accreditation.partner_id.name} - {accreditation.collection_date} - Batch: {accreditation.batch_number or "N/A"} - Coupon: {accreditation.coupon_number or "N/A"}',
                    'quantity': 1,
                    'price_unit': accreditation.financial_cost,
                    'account_id': self._get_financial_cost_expense_account(accreditation),
                }
                invoice_vals['invoice_line_ids'].append((0, 0, financial_line_vals))
        
        # Create the invoice
        invoice = self.env['account.move'].create(invoice_vals)
        
        # Mark accreditations as invoiced
        for accreditation in self.accreditation_ids:
            updates = {}
            if accreditation.fee > 0 and not accreditation.fee_invoiced:
                updates['fee_invoiced'] = True
            if (self.include_financial_cost and 
                accreditation.financial_cost > 0 and 
                not accreditation.financial_cost_invoiced):
                updates['financial_cost_invoiced'] = True
            
            if updates:
                accreditation.write(updates)
        
        # Log activity on each accreditation
        for accreditation in self.accreditation_ids:
            invoice_items = []
            if accreditation.fee > 0 and not accreditation.fee_invoiced:
                invoice_items.append(f'Fee: {accreditation.fee}')
            if (self.include_financial_cost and 
                accreditation.financial_cost > 0 and 
                not accreditation.financial_cost_invoiced):
                invoice_items.append(f'Financial Cost: {accreditation.financial_cost}')
            
            if invoice_items:
                accreditation.message_post(
                    body=f'Invoiced to {self.partner_id.name} in invoice {invoice.name}: {", ".join(invoice_items)}',
                    subtype_xmlid='mail.mt_note'
                )
        
        # Return action to open the created invoice
        return {
            'type': 'ir.actions.act_window',
            'name': _('Credit Card Costs Invoice'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _get_fee_expense_account(self, accreditation):
        """Get the expense account for fee from card plan or default"""
        if accreditation.card_plan_id and accreditation.card_plan_id.fee_account_id:
            return accreditation.card_plan_id.fee_account_id.id
        
        # Fallback to company's default expense account or create one
        company = self.env.company
        expense_account = self.env['account.account'].search([
            ('company_id', '=', company.id),
            ('account_type', '=', 'expense'),
            ('code', 'like', '6%')
        ], limit=1)
        
        if not expense_account:
            raise UserError(_(
                'No expense account found. Please configure a fee account '
                'in the card plan or create an expense account.'
            ))
        
        return expense_account.id

    def _get_financial_cost_expense_account(self, accreditation):
        """Get the expense account for financial cost"""
        # Try to get from card plan if it has a specific financial cost account
        if accreditation.card_plan_id and hasattr(accreditation.card_plan_id, 'financial_cost_account_id'):
            if accreditation.card_plan_id.financial_cost_account_id:
                return accreditation.card_plan_id.financial_cost_account_id.id
        
        # Fallback to general financial expense account
        company = self.env.company
        financial_expense_account = self.env['account.account'].search([
            ('company_id', '=', company.id),
            ('account_type', '=', 'expense'),
            ('code', 'like', '65%')  # Financial expenses typically start with 65
        ], limit=1)
        
        if not financial_expense_account:
            # If no specific financial expense account, use general expense account
            expense_account = self.env['account.account'].search([
                ('company_id', '=', company.id),
                ('account_type', '=', 'expense'),
                ('code', 'like', '6%')
            ], limit=1)
            
            if not expense_account:
                raise UserError(_(
                    'No expense account found for financial costs. Please configure '
                    'a financial expense account or create an expense account.'
                ))
            return expense_account.id
        
        return financial_expense_account.id

    def _get_financial_cost_expense_account(self, accreditation):
        """Get the expense account for financial cost from card plan or default"""
        if accreditation.card_plan_id and hasattr(accreditation.card_plan_id, 'financial_cost_account_id') and accreditation.card_plan_id.financial_cost_account_id:
            return accreditation.card_plan_id.financial_cost_account_id.id
        
        # Fallback to company's default financial expense account
        company = self.env.company
        financial_expense_account = self.env['account.account'].search([
            ('company_id', '=', company.id),
            ('account_type', '=', 'expense'),
            ('code', 'like', '62%'),  # Financial expenses typically start with 62
            ('name', 'ilike', 'financial')
        ], limit=1)
        
        # If no specific financial account, use general expense account
        if not financial_expense_account:
            financial_expense_account = self.env['account.account'].search([
                ('company_id', '=', company.id),
                ('account_type', '=', 'expense'),
                ('code', 'like', '6%')
            ], limit=1)
        
        if not financial_expense_account:
            raise UserError(_(
                'No expense account found for financial costs. Please configure a financial cost account '
                'in the card plan or create an expense account for financial costs.'
            ))
        
        return financial_expense_account.id