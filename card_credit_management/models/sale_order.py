# © 2025 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    card_plan_id = fields.Many2one(
        'card.plan',
        string='Credit Card Plan',
        help='Selected credit card plan for surcharge calculation'
    )
    
    card_surcharge_amount = fields.Monetary(
        string='Card Surcharge Amount',
        currency_field='currency_id',
        readonly=True,
        help='Calculated surcharge amount based on selected card plan'
    )
    
    card_surcharge_calculated = fields.Boolean(
        string='Surcharge Calculated',
        default=False,
        help='Indicates if surcharge has been calculated for current order total'
    )
    
    card_base_amount = fields.Monetary(
        string='Base Amount for Surcharge',
        currency_field='currency_id',
        readonly=True,
        help='Base amount used for surcharge calculation'
    )

    @api.depends('card_plan_id', 'order_line.price_subtotal')
    def _compute_card_surcharge_needs_recalculation(self):
        """Determina si el recargo necesita ser recalculado"""
        for order in self:
            if not order.card_plan_id or not order.card_surcharge_calculated:
                order.card_surcharge_needs_recalculation = False
                continue
            
            # Calcular el monto base actual (sin líneas de recargo)
            current_base = sum(
                line.price_subtotal 
                for line in order.order_line 
                if not line.is_card_surcharge
            )
            
            # Comparar con el monto base almacenado
            order.card_surcharge_needs_recalculation = abs(current_base - order.card_base_amount) > 0.01

    card_surcharge_needs_recalculation = fields.Boolean(
        string='Surcharge Needs Recalculation',
        compute='_compute_card_surcharge_needs_recalculation',
        store=True,
        help='Indicates if surcharge needs to be recalculated due to order changes'
    )

    @api.depends('card_plan_id', 'card_surcharge_calculated', 'card_surcharge_needs_recalculation')
    def _compute_card_surcharge_visibility(self):
        for order in self:
            # Mostrar botón si hay plan y no está calculado, O si necesita recálculo
            order.show_calculate_surcharge_button = bool(
                order.card_plan_id and 
                (not order.card_surcharge_calculated or order.card_surcharge_needs_recalculation)
            )

    show_calculate_surcharge_button = fields.Boolean(
        string='Show Calculate Surcharge Button',
        compute='_compute_card_surcharge_visibility',
        help='Shows calculate surcharge button when needed'
    )

    @api.onchange('card_plan_id')
    def _onchange_card_plan_id(self):
        """Reset surcharge calculation when plan changes"""
        if self.card_plan_id:
            self.card_surcharge_calculated = False
            self.card_surcharge_amount = 0
            self.card_base_amount = 0

    def action_calculate_card_surcharge(self):
        """Calcula el recargo de tarjeta de crédito"""
        self.ensure_one()
        
        if not self.card_plan_id:
            raise UserError(_('Please select a credit card plan first.'))
        
        # Remover líneas de recargo existentes
        existing_surcharge_lines = self.order_line.filtered(lambda line: line.is_card_surcharge)
        existing_surcharge_lines.unlink()
        
        # Calcular monto base (sin recargo)
        base_amount = sum(line.price_subtotal for line in self.order_line if not line.is_card_surcharge)
        
        if base_amount > 0:
            surcharge_amount = self.card_plan_id.calculate_surcharge(base_amount)
            
            if surcharge_amount > 0:
                # Crear nueva línea de recargo
                self._create_surcharge_line(surcharge_amount)
                
                # Actualizar campos de control
                self.card_surcharge_calculated = True
                self.card_base_amount = base_amount
                self.card_surcharge_amount = surcharge_amount
            else:
                # No hay recargo
                self.card_surcharge_calculated = True
                self.card_base_amount = base_amount
                self.card_surcharge_amount = 0
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Surcharge Calculated'),
                'message': _('Credit card surcharge has been calculated and added to the order.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def _create_surcharge_line(self, surcharge_amount):
        """Crea o actualiza la línea de recargo"""
        self.ensure_one()
        
        # Buscar línea de recargo existente
        surcharge_line = self.order_line.filtered(lambda l: l.is_card_surcharge)
        
        if surcharge_line:
            # Actualizar línea existente
            surcharge_line.price_unit = surcharge_amount
        else:
            # Crear nueva línea
            surcharge_product = self._get_surcharge_product()
            self.env['sale.order.line'].create({
                'order_id': self.id,
                'product_id': surcharge_product.id,
                'name': _('Credit Card Surcharge - %s') % self.card_plan_id.name,
                'product_uom_qty': 1,
                'price_unit': surcharge_amount,
                'is_card_surcharge': True,
            })

    def _get_surcharge_product(self):
        """Obtiene o crea el producto para recargo de tarjeta"""
        surcharge_product = self.env.ref('card_credit_management.product_card_surcharge', raise_if_not_found=False)
        
        if not surcharge_product:
            # Crear producto si no existe
            surcharge_product = self.env['product.product'].create({
                'name': _('Credit Card Surcharge'),
                'type': 'service',
                'invoice_policy': 'order',
                'categ_id': self.env.ref('product.product_category_all').id,
            })
        
        return surcharge_product

    def action_confirm(self):
        """Override para validar consistencia del recargo antes de confirmar"""
        for order in self:
            if order.card_plan_id and order.card_surcharge_needs_recalculation:
                # Solo validar si realmente necesita recálculo
                raise ValidationError(_(
                    'The order total has changed since the surcharge was calculated. '
                    'Please recalculate the surcharge before confirming the order.'
                ))
        
        return super().action_confirm()

    def _prepare_invoice(self):
        """Override para transferir información de tarjeta a la factura"""
        invoice_vals = super()._prepare_invoice()
        
        if self.card_plan_id:
            invoice_vals.update({
                'card_plan_id': self.card_plan_id.id,
                'card_surcharge_amount': self.card_surcharge_amount,
            })
        
        return invoice_vals


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_card_surcharge = fields.Boolean(
        string='Is Card Surcharge',
        default=False,
        help='Indicates if this line is a credit card surcharge'
    )

    def _prepare_invoice_line(self, **optional_values):
        """Override para configurar cuenta contable del recargo"""
        vals = super()._prepare_invoice_line(**optional_values)
        
        if self.is_card_surcharge and self.order_id.card_plan_id:
            # Usar cuenta de costo financiero para el recargo
            financial_account = self.order_id.card_plan_id.financial_cost_account_id
            if financial_account:
                vals['account_id'] = financial_account.id
        
        return vals