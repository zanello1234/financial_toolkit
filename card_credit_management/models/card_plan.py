# © 2025 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class CardPlan(models.Model):
    _name = 'card.plan'
    _description = 'Credit Card Plan'
    _order = 'journal_id, name'

    name = fields.Char(
        string='Plan Name',
        required=True,
        help='Name of the credit card plan (e.g., Cuota Simple Tres, Débito)'
    )
    
    journal_id = fields.Many2one(
        'account.journal',
        string='Associated Journal',
        required=True,
        domain=[('type', '=', 'bank'), ('is_credit_card', '=', True)],
        help='Credit card journal (Visa, Mastercard, etc.)'
    )
    
    accreditation_days = fields.Integer(
        string='Accreditation Days',
        required=True,
        default=2,
        help='Number of business days for accreditation (e.g., 2 for debit, 10 for installments)'
    )
    
    fee_percentage = fields.Float(
        string='Fee Percentage',
        digits=(16, 4),
        default=1.8,
        help='Fee percentage (e.g., 1.8% + VAT)'
    )
    
    financial_cost_percentage = fields.Float(
        string='Financial Cost Percentage',
        digits=(16, 4),
        default=5.87,
        help='Financial cost percentage (e.g., 5.87%)'
    )
    
    surcharge_coefficient = fields.Float(
        string='Surcharge Coefficient',
        digits=(16, 6),
        required=True,
        help='Coefficient used for surcharge calculation in sales'
    )
    
    rounding_factor = fields.Selection([
        ('1', '1'),
        ('10', '10'),
        ('100', '100'),
        ('1000', '1000'),
    ], string='Rounding Factor', default='10',
       help='Multiple to round the calculated surcharge and avoid decimals in prices')
    
    active = fields.Boolean(default=True)
    
    # Cuentas contables configurables
    fee_account_id = fields.Many2one(
        'account.account',
        string='Fee Account',
        help='Account for fees and bank charges'
    )
    
    financial_cost_account_id = fields.Many2one(
        'account.account',
        string='Financial Cost Account',
        help='Account for financial costs/interests'
    )
    
    vat_account_id = fields.Many2one(
        'account.account',
        string='VAT Account',
        help='Account for VAT credit'
    )
    
    gross_income_account_id = fields.Many2one(
        'account.account',
        string='Gross Income Account',
        help='Account for gross income taxes (Sirtac, etc.)'
    )

    @api.constrains('fee_percentage', 'financial_cost_percentage', 'surcharge_coefficient')
    def _check_percentages(self):
        for record in self:
            if record.fee_percentage < 0:
                raise ValidationError(_('Fee percentage cannot be negative'))
            if record.financial_cost_percentage < 0:
                raise ValidationError(_('Financial cost percentage cannot be negative'))
            if record.surcharge_coefficient <= 0:
                raise ValidationError(_('Surcharge coefficient must be positive'))

    @api.constrains('accreditation_days')
    def _check_accreditation_days(self):
        for record in self:
            if record.accreditation_days <= 0:
                raise ValidationError(_('Accreditation days must be positive'))

    def calculate_estimated_amount(self, original_amount):
        """Calcula el monto estimado a liquidar restando arancel y costo financiero"""
        self.ensure_one()
        fee_amount = original_amount * (self.fee_percentage / 100)
        financial_cost = original_amount * (self.financial_cost_percentage / 100)
        estimated_amount = original_amount - fee_amount - financial_cost
        return estimated_amount

    def calculate_surcharge(self, base_amount):
        """Calcula el recargo basado en el coeficiente y factor de redondeo"""
        self.ensure_one()
        surcharge = base_amount * (self.surcharge_coefficient - 1)
        rounding_factor = int(self.rounding_factor)
        
        # Redondear según el factor configurado
        if rounding_factor > 1:
            surcharge = round(surcharge / rounding_factor) * rounding_factor
            
        return surcharge

    def calculate_accreditation_date(self, collection_date):
        """Calcula la fecha estimada de acreditación considerando días hábiles y feriados"""
        self.ensure_one()
        
        # Buscar días feriados
        holidays = self.env['card.holiday'].search([])
        holiday_dates = [h.date for h in holidays]
        
        current_date = collection_date
        business_days_count = 0
        
        while business_days_count < self.accreditation_days:
            current_date = fields.Date.add(current_date, days=1)
            
            # Verificar si es día laboral (lunes=0, domingo=6)
            weekday = current_date.weekday()
            if weekday < 5 and current_date not in holiday_dates:  # Lunes a Viernes y no feriado
                business_days_count += 1
        
        return current_date

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.journal_id.name} - {record.name}"
            result.append((record.id, name))
        return result