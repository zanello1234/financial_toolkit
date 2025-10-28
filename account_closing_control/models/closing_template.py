# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ClosingTemplate(models.Model):
    _name = 'closing.template'
    _description = 'Plantilla de Cierre Contable'
    _order = 'name'

    name = fields.Char(
        string='Nombre',
        required=True,
        help='Ej: "Cierre Mensual", "Cierre Anual"'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company
    )
    
    periodicity = fields.Selection([
        ('monthly', 'Mensual'),
        ('quarterly', 'Trimestral'),
        ('annually', 'Anual')
    ], string='Periodicidad', required=True, default='monthly')
    
    description = fields.Html(
        string='Descripción',
        help='Descripción de la plantilla y objetivos del proceso de cierre'
    )
    
    active = fields.Boolean(
        string='Activo',
        default=True
    )
    
    line_ids = fields.One2many(
        'closing.template.line',
        'template_id',
        string='Líneas de la Plantilla'
    )
    
    line_count = fields.Integer(
        string='Número de Tareas',
        compute='_compute_line_count'
    )
    
    @api.depends('line_ids')
    def _compute_line_count(self):
        for record in self:
            record.line_count = len(record.line_ids)

    def action_view_worksheets(self):
        """Acción para ver las hojas de cierre creadas a partir de esta plantilla"""
        action = self.env.ref('account_closing_control.action_closing_worksheet').read()[0]
        worksheets = self.env['closing.worksheet'].search([('template_id', '=', self.id)])
        if len(worksheets) == 1:
            action['views'] = [(self.env.ref('account_closing_control.view_closing_worksheet_form').id, 'form')]
            action['res_id'] = worksheets.id
        else:
            action['domain'] = [('template_id', '=', self.id)]
        action['context'] = {'default_template_id': self.id}
        return action

    def action_generate_worksheet(self):
        action = self.env.ref('account_closing_control.action_closing_wizard').read()[0]
        action['context'] = {'default_template_id': self.id}
        return action

    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = _('%s (Copia)') % self.name
        return super().copy(default)