# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    # Credit card statement specific fields
    closing_date = fields.Date(
        string='Fecha de Cierre',
        help="Closing date for credit card statement"
    )
    due_date = fields.Date(
        string='Fecha de Vencimiento', 
        help="Due date for credit card statement payment"
    )
    
    # Debt amounts by currency
    debt_ars = fields.Monetary(
        string='Deuda en Pesos',
        currency_field='currency_id',
        help="Outstanding debt in ARS when statement was closed"
    )
    debt_usd = fields.Monetary(
        string='Deuda en Dólares',
        currency_field='currency_id', 
        help="Outstanding debt in USD when statement was closed"
    )
    
    is_credit_card_statement = fields.Boolean(
        string='Is Credit Card Statement',
        default=False,
        help="Indicates if this is a credit card statement"
    )
    
    # Statement totals by currency
    statement_total_ars = fields.Monetary(
        string='Total a Pagar (ARS)',
        currency_field='currency_id',
        help="Total amount to pay in ARS from this statement"
    )
    statement_total_usd = fields.Monetary(
        string='Total a Pagar (USD)', 
        currency_field='currency_id',
        help="Total amount to pay in USD from this statement"
    )
    statement_total_general = fields.Monetary(
        string='Total General',
        currency_field='currency_id', 
        help="Total general amount (ARS + USD converted to ARS)"
    )
    
    # Account balance at statement closing
    account_balance = fields.Monetary(
        string='Saldo Cuenta Contable',
        currency_field='currency_id',
        help="Credit card account balance at statement closing date"
    )
    
    def write(self, vals):
        """Override write to ensure ending balance equals debt for credit card statements"""
        result = super().write(vals)
        
        # For credit card statements, ensure ending balance equals the debt amount
        for statement in self:
            if statement.is_credit_card_statement and statement.statement_total_general:
                if 'statement_total_general' in vals or 'is_credit_card_statement' in vals:
                    # Update ending balance to match debt amount
                    super(AccountBankStatement, statement).write({
                        'balance_end_real': statement.statement_total_general
                    })
        
        return result