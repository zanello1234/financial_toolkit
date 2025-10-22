# -*- coding: utf-8 -*-
from odoo import models, fields

class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    # Solo mantenemos el campo por si acaso o para futura referencia/debug,
    # pero ya no se usa activamente en la lógica de modificación del asiento.
    x_adjustment_account_id = fields.Many2one(
        'account.account',
        string='Custom Adjustment Account',
        company_dependent=True,
        copy=False,
        readonly=True,
    )