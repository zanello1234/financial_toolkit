# © 2025 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    card_plan_id = fields.Many2one(
        'card.plan',
        string='Credit Card Plan',
        help='Credit card plan used for this invoice'
    )
    
    card_surcharge_amount = fields.Monetary(
        string='Card Surcharge Amount',
        currency_field='currency_id',
        help='Credit card surcharge amount from sale order'
    )

    def _post(self, soft=True):
        """Override para configurar cuentas contables de líneas de recargo"""
        result = super()._post(soft)
        
        for move in self:
            if move.card_plan_id:
                # Configurar cuentas para líneas de recargo
                surcharge_lines = move.invoice_line_ids.filtered(
                    lambda l: l.sale_line_ids and l.sale_line_ids.is_card_surcharge
                )
                
                for line in surcharge_lines:
                    if move.card_plan_id.financial_cost_account_id:
                        line.account_id = move.card_plan_id.financial_cost_account_id
        
        return result


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_card_surcharge = fields.Boolean(
        string='Is Card Surcharge',
        related='sale_line_ids.is_card_surcharge',
        store=True,
        help='Indicates if this line comes from a credit card surcharge'
    )