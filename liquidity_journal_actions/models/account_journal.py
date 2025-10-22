from odoo import models, fields, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    @api.depends('type')
    def _compute_is_liquidity_journal(self):
        for journal in self:
            journal.is_liquidity_journal = journal.type in ('bank', 'cash')

    is_liquidity_journal = fields.Boolean(
        string="Es Diario de Liquidez",
        compute='_compute_is_liquidity_journal',
        store=True,
        help="Indica si el diario es de tipo banco o efectivo"
    )

    def action_create_payment(self):
        """Abrir vista de creación de pagos (salida) o wizard de cambio para moneda extranjera"""
        if self.currency_id and self.currency_id != self.company_id.currency_id:
            # Moneda extranjera - abrir wizard de cambio
            return {
                'name': 'Vender ' + self.currency_id.name,
                'type': 'ir.actions.act_window',
                'res_model': 'currency.exchange.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_journal_id': self.id,
                    'default_operation_type': 'sell',
                }
            }
        else:
            # Moneda local - formulario normal de pagos
            return {
                'name': 'Crear Pago',
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment',
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'default_journal_id': self.id,
                    'default_payment_type': 'outbound',
                    'default_partner_type': 'supplier',
                }
            }

    def action_create_collection(self):
        """Abrir vista de creación de cobros (entrada) o wizard de cambio para moneda extranjera"""
        if self.currency_id and self.currency_id != self.company_id.currency_id:
            # Moneda extranjera - abrir wizard de cambio
            return {
                'name': 'Comprar ' + self.currency_id.name,
                'type': 'ir.actions.act_window',
                'res_model': 'currency.exchange.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_journal_id': self.id,
                    'default_operation_type': 'buy',
                }
            }
        else:
            # Moneda local - formulario normal de cobros
            return {
                'name': 'Crear Cobro',
                'type': 'ir.actions.act_window',
                'res_model': 'account.payment',
                'view_mode': 'form',
                'target': 'current',
                'context': {
                    'default_journal_id': self.id,
                    'default_payment_type': 'inbound',
                    'default_partner_type': 'customer',
                }
            }

    def action_create_transfer(self):
        """Abrir wizard de transferencia interna"""
        return {
            'name': 'Transferencia Interna',
            'type': 'ir.actions.act_window',
            'res_model': 'internal.transfer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_source_journal_id': self.id,
            }
        }

    def action_view_payments(self):
        """Ver todos los pagos del diario"""
        action = self.env.ref('account.action_account_payments').read()[0]
        action.update({
            'name': f'Pagos del Diario - {self.name}',
            'domain': [('journal_id', '=', self.id)],
            'context': {
                'default_journal_id': self.id,
                'search_default_journal_id': self.id,
            }
        })
        return action