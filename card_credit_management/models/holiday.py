# © 2025 ADHOC SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Holiday(models.Model):
    _name = 'card.holiday'
    _description = 'Holidays for Credit Card Accreditation Calculation'
    _order = 'date desc'

    name = fields.Char(
        string='Holiday Name',
        required=True,
        help='Name of the holiday (e.g., Christmas, New Year)'
    )
    
    date = fields.Date(
        string='Date',
        required=True,
        help='Holiday date'
    )
    
    recurring = fields.Boolean(
        string='Recurring',
        default=False,
        help='If true, this holiday occurs every year on the same day'
    )
    
    active = fields.Boolean(default=True)
    
    notes = fields.Text(
        string='Notes',
        help='Additional notes about this holiday'
    )

    @api.constrains('date')
    def _check_unique_date(self):
        for record in self:
            existing = self.search([
                ('date', '=', record.date),
                ('id', '!=', record.id)
            ])
            if existing:
                raise ValidationError(_('A holiday already exists for this date: %s') % record.date)

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.name} ({record.date})"
            result.append((record.id, name))
        return result