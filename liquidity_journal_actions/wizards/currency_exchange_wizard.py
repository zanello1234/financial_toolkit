from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CurrencyExchangeWizard(models.TransientModel):
    _name = 'currency.exchange.wizard'
    _description = 'Wizard para compra/venta de divisas con transferencia interna'

    operation_type = fields.Selection([
        ('buy', 'Comprar'),
        ('sell', 'Vender')
    ], string='Tipo de Operación', required=True)
    
    journal_id = fields.Many2one(
        'account.journal',
        string='Diario Divisa',
        required=True,
        domain="[('type', 'in', ('bank', 'cash')), ('currency_id', '!=', False)]"
    )
    
    amount_currency = fields.Monetary(
        string='Cantidad en Divisa',
        required=True,
        currency_field='foreign_currency_id'
    )
    
    foreign_currency_id = fields.Many2one(
        'res.currency',
        string='Moneda Extranjera',
        related='journal_id.currency_id',
        readonly=True
    )
    
    exchange_rate = fields.Float(
        string='Tipo de Cambio',
        required=True,
        digits=(12, 6),
        help='1 unidad de moneda extranjera = X unidades de moneda local'
    )
    
    amount_company = fields.Monetary(
        string='Monto en Moneda Local',
        compute='_compute_amount_company',
        currency_field='company_currency_id'
    )
    
    company_currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )
    
    local_journal_id = fields.Many2one(
        'account.journal',
        string='Diario Local',
        required=True,
        domain="[('type', 'in', ('bank', 'cash')), ('currency_id', 'in', [False, company_currency_id])]"
    )
    
    memo = fields.Char(
        string='Referencia',
        help='Descripción de la operación de cambio'
    )
    
    date = fields.Date(
        string='Fecha',
        default=fields.Date.context_today,
        required=True
    )

    @api.depends('amount_currency', 'exchange_rate')
    def _compute_amount_company(self):
        for record in self:
            if record.amount_currency and record.exchange_rate:
                record.amount_company = record.amount_currency * record.exchange_rate
            else:
                record.amount_company = 0.0

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if self.journal_id and self.journal_id.currency_id:
            self.foreign_currency_id = self.journal_id.currency_id
            # Obtener tipo de cambio actual
            rate = self.foreign_currency_id._get_conversion_rate(
                from_currency=self.foreign_currency_id,
                to_currency=self.company_currency_id,
                company=self.env.company,
                date=self.date or fields.Date.today()
            )
            self.exchange_rate = rate

    @api.constrains('amount_currency', 'exchange_rate')
    def _check_amounts(self):
        for record in self:
            if record.amount_currency <= 0:
                raise ValidationError(_('La cantidad en divisa debe ser mayor a cero.'))
            if record.exchange_rate <= 0:
                raise ValidationError(_('El tipo de cambio debe ser mayor a cero.'))

    def action_create_internal_transfer(self):
        """Crear la transferencia interna basada en la operación"""
        self.ensure_one()
        
        if not self.journal_id or not self.local_journal_id:
            raise ValidationError(_('Debe seleccionar ambos diarios.'))
        
        # Verificar que existe cuenta de transferencia configurada
        if not self.env.company.transfer_account_id:
            raise ValidationError(_('Debe configurar una cuenta de transferencia interna en la configuración de la compañía.'))
        
        try:
            if self.operation_type == 'buy':
                # COMPRAR: Crear transferencia usando dos asientos separados como en la venta
                # Primero: Pago desde diario local (ARS) hacia cuenta de transferencia
                payment_local = self.env['account.payment'].create({
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'journal_id': self.local_journal_id.id,
                    'amount': self.amount_company,
                    'currency_id': self.company_currency_id.id,
                    'date': self.date,
                    'memo': self.memo or f"Compra de {self.foreign_currency_id.name}",
                    'is_internal_transfer': True,
                    'destination_journal_id': self.journal_id.id,
                    'destination_account_id': self.env.company.transfer_account_id.id,
                })
                payment_local.action_post()
                
                # Segundo: Crear movimiento de entrada en el diario de divisa
                move_vals = {
                    'journal_id': self.journal_id.id,
                    'date': self.date,
                    'ref': self.memo or f"Compra de {self.foreign_currency_id.name}",
                    'line_ids': [
                        # Débito en cuenta del diario de divisa (entrada de USD)
                        (0, 0, {
                            'account_id': self.journal_id.default_account_id.id,
                            'debit': self.amount_company,
                            'credit': 0,
                            'amount_currency': self.amount_currency,
                            'currency_id': self.foreign_currency_id.id,
                            'name': f"Compra de {self.foreign_currency_id.name}",
                        }),
                        # Crédito en cuenta de transferencia
                        (0, 0, {
                            'account_id': self.env.company.transfer_account_id.id,
                            'debit': 0,
                            'credit': self.amount_company,
                            'amount_currency': -self.amount_currency,
                            'currency_id': self.foreign_currency_id.id,
                            'name': f"Transferencia por compra de {self.foreign_currency_id.name}",
                        }),
                    ]
                }
                
                move = self.env['account.move'].create(move_vals)
                move.action_post()
                
                # Reconciliar las líneas de la cuenta de transferencia
                lines_to_reconcile = (payment_local.move_id.line_ids + move.line_ids).filtered(
                    lambda l: l.account_id == self.env.company.transfer_account_id and not l.reconciled
                )
                if lines_to_reconcile:
                    lines_to_reconcile.reconcile()
                
                payment_to_show = payment_local
                
            else:
                # VENDER: Crear pago desde diario de divisa hacia cuenta de transferencia
                payment_foreign = self.env['account.payment'].create({
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'journal_id': self.journal_id.id,
                    'amount': self.amount_currency,
                    'currency_id': self.foreign_currency_id.id,
                    'date': self.date,
                    'memo': self.memo or f"Venta de {self.foreign_currency_id.name}",
                    'is_internal_transfer': True,
                    'destination_journal_id': self.local_journal_id.id,
                    'destination_account_id': self.env.company.transfer_account_id.id,
                })
                payment_foreign.action_post()
                
                # Crear movimiento de entrada en el diario local
                move_vals = {
                    'journal_id': self.local_journal_id.id,
                    'date': self.date,
                    'ref': self.memo or f"Venta de {self.foreign_currency_id.name}",
                    'line_ids': [
                        (0, 0, {
                            'account_id': self.local_journal_id.default_account_id.id,
                            'debit': self.amount_company,
                            'credit': 0,
                            'amount_currency': 0,
                            'currency_id': self.company_currency_id.id,
                            'name': f"Venta de {self.foreign_currency_id.name}",
                        }),
                        (0, 0, {
                            'account_id': self.env.company.transfer_account_id.id,
                            'debit': 0,
                            'credit': self.amount_company,
                            'amount_currency': -self.amount_currency,
                            'currency_id': self.foreign_currency_id.id,
                            'name': f"Transferencia por venta de {self.foreign_currency_id.name}",
                        }),
                    ]
                }
                
                move = self.env['account.move'].create(move_vals)
                move.action_post()
                payment_to_show = payment_foreign
                
            return {
                'name': _('Operación de Cambio Creada'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move' if self.operation_type == 'buy' else 'account.payment',
                'res_id': payment_to_show.id,
                'view_mode': 'form',
                'target': 'current',
            }
            
        except Exception as e:
            raise ValidationError(_(
                'Error al crear la transferencia interna: %s\n\n'
                'Verifique que:\n'
                '- Los diarios tengan configuradas las cuentas correspondientes\n'
                '- La cuenta de transferencia interna esté configurada\n'
                '- Las monedas estén correctamente configuradas'
            ) % str(e))