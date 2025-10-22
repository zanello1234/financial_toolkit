# © 2025 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CardSurchargeWizard(models.TransientModel):
    _name = 'card.surcharge.wizard'
    _description = 'Credit Card Surcharge Calculation Wizard'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True,
        readonly=True
    )
    
    card_plan_id = fields.Many2one(
        'card.plan',
        string='Credit Card Plan',
        required=True,
        help='Select the credit card plan for surcharge calculation'
    )
    
    base_amount = fields.Monetary(
        string='Base Amount',
        readonly=True,
        currency_field='currency_id',
        help='Amount used as base for surcharge calculation'
    )
    
    surcharge_amount = fields.Monetary(
        string='Surcharge Amount',
        readonly=True,
        currency_field='currency_id',
        help='Calculated surcharge amount'
    )
    
    total_amount = fields.Monetary(
        string='Total Amount',
        readonly=True,
        currency_field='currency_id',
        help='Total amount including surcharge'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='sale_order_id.currency_id',
        readonly=True
    )

    @api.onchange('card_plan_id')
    def _onchange_card_plan_id(self):
        """Recalcular recargo cuando cambia el plan"""
        if self.card_plan_id and self.sale_order_id:
            # Calcular monto base (total actual menos recargo previo)
            current_surcharge = self.sale_order_id.card_surcharge_amount or 0
            self.base_amount = self.sale_order_id.amount_total - current_surcharge
            
            # Calcular nuevo recargo
            self.surcharge_amount = self.card_plan_id.calculate_surcharge(self.base_amount)
            self.total_amount = self.base_amount + self.surcharge_amount

    def action_apply_surcharge(self):
        """Aplicar el recargo calculado a la orden de venta"""
        self.ensure_one()
        
        if not self.card_plan_id:
            raise UserError(_('Please select a credit card plan.'))
        
        # Actualizar orden de venta
        self.sale_order_id.write({
            'card_plan_id': self.card_plan_id.id,
            'card_surcharge_amount': self.surcharge_amount,
            'card_base_amount': self.base_amount,
            'card_surcharge_calculated': True,
        })
        
        # Crear o actualizar línea de recargo
        self.sale_order_id._create_surcharge_line(self.surcharge_amount)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Surcharge Applied'),
                'message': _('Credit card surcharge has been successfully applied to the order.'),
                'type': 'success',
                'sticky': False,
            }
        }

    @api.model
    def default_get(self, fields_list):
        """Configurar valores por defecto"""
        result = super().default_get(fields_list)
        
        sale_order_id = self.env.context.get('active_id')
        if sale_order_id:
            sale_order = self.env['sale.order'].browse(sale_order_id)
            result.update({
                'sale_order_id': sale_order.id,
                'card_plan_id': sale_order.card_plan_id.id,
            })
        
        return result