# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class ClosingTemplateLine(models.Model):
    _name = 'closing.template.line'
    _description = 'Línea de Plantilla de Cierre'
    _order = 'sequence, id'

    template_id = fields.Many2one(
        'closing.template',
        string='Plantilla',
        required=True,
        ondelete='cascade'
    )
    
    name = fields.Char(
        string='Tarea',
        required=True,
        help='Ej: "Conciliar Bancos", "Revisar Inventarios"'
    )
    
    description = fields.Html(
        string='Instrucciones',
        help='Instrucciones detalladas para el analista'
    )
    
    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Orden de ejecución de las tareas'
    )
    
    validation_type = fields.Selection([
        ('manual', 'Manual'),
        ('action', 'Acción'),
        ('python', 'Python')
    ], string='Tipo de Validación', required=True, default='manual',
    help="""
    Manual: El analista marca manualmente como completado
    Acción: Abre una vista específica de Odoo para realizar la tarea
    Python: Ejecuta código Python para validar automáticamente
    """)
    
    related_action_id = fields.Many2one(
        'ir.actions.act_window',
        string='Acción Relacionada',
        help='Acción de Odoo a ejecutar (solo para tipo "Acción")'
    )
    
    python_code = fields.Text(
        string='Código Python',
        help='Código Python a ejecutar para validación automática'
    )
    
    required = fields.Boolean(
        string='Obligatorio',
        default=True,
        help='Si es obligatorio completar esta tarea para aprobar el cierre'
    )
    
    responsible_group_id = fields.Many2one(
        'res.groups',
        string='Grupo Responsable',
        help='Grupo de usuarios responsable de ejecutar esta tarea'
    )

    @api.constrains('validation_type', 'related_action_id', 'python_code')
    def _check_validation_fields(self):
        for line in self:
            if line.validation_type == 'action' and not line.related_action_id:
                raise ValidationError(_("Debe especificar una acción relacionada para el tipo de validación 'Acción'."))
            if line.validation_type == 'python' and not line.python_code:
                raise ValidationError(_("Debe especificar código Python para el tipo de validación 'Python'."))