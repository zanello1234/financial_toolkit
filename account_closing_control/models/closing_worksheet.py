# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date
import logging

_logger = logging.getLogger(__name__)


class ClosingWorksheet(models.Model):
    _name = 'closing.worksheet'
    _description = 'Hoja de Cierre Contable'
    _inherit = ['mail.thread']
    _order = 'date_to desc, id desc'

    name = fields.Char(
        string='Nombre',
        required=True,
        copy=False,
        help='Ej: "Cierre 10/2025"'
    )
    
    template_id = fields.Many2one(
        'closing.template',
        string='Plantilla',
        required=True,
        tracking=True
    )
    
    date_from = fields.Date(
        string='Fecha Inicio',
        required=True,
        tracking=True
    )
    
    date_to = fields.Date(
        string='Fecha Fin',
        required=True,
        tracking=True
    )
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('in_progress', 'En Progreso'),
        ('to_review', 'A Revisar'),
        ('done', 'Cerrado'),
        ('cancel', 'Cancelado')
    ], string='Estado', default='draft', required=True, tracking=True)
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company
    )
    
    line_ids = fields.One2many(
        'closing.worksheet.line',
        'worksheet_id',
        string='Tareas de Cierre'
    )
    
    summary = fields.Html(
        string='Resumen',
        help='Notas de resumen del cierre'
    )
    
    created_by = fields.Many2one(
        'res.users',
        string='Creado por',
        default=lambda self: self.env.user,
        readonly=True
    )
    
    approved_by = fields.Many2one(
        'res.users',
        string='Aprobado por',
        readonly=True,
        tracking=True
    )
    
    approved_date = fields.Datetime(
        string='Fecha de Aprobación',
        readonly=True,
        tracking=True
    )
    
    lock_date_set = fields.Date(
        string='Fecha de Bloqueo Contable',
        readonly=True,
        help='Fecha hasta la cual se bloquearon los asientos de ventas/compras'
    )
    
    tax_lock_date_set = fields.Date(
        string='Fecha de Bloqueo Fiscal',
        readonly=True,
        help='Fecha hasta la cual se bloquearon los asientos fiscales'
    )
    
    # Campos computados para estadísticas
    progress_percentage = fields.Float(
        string='Progreso %',
        compute='_compute_progress',
        store=True
    )
    
    total_tasks = fields.Integer(
        string='Total Tareas',
        compute='_compute_task_stats',
        store=True
    )
    
    completed_tasks = fields.Integer(
        string='Tareas Completadas',
        compute='_compute_task_stats',
        store=True
    )
    
    pending_tasks = fields.Integer(
        string='Tareas Pendientes',
        compute='_compute_task_stats',
        store=True
    )
    
    failed_tasks = fields.Integer(
        string='Tareas Fallidas',
        compute='_compute_task_stats',
        store=True
    )

    @api.depends('line_ids.state')
    def _compute_progress(self):
        for record in self:
            total = len(record.line_ids)
            if total == 0:
                record.progress_percentage = 0.0
            else:
                completed = len(record.line_ids.filtered(lambda l: l.state in ('done', 'skipped')))
                record.progress_percentage = (completed / total) * 100.0

    @api.depends('line_ids.state')
    def _compute_task_stats(self):
        for record in self:
            lines = record.line_ids
            record.total_tasks = len(lines)
            record.completed_tasks = len(lines.filtered(lambda l: l.state == 'done'))
            record.pending_tasks = len(lines.filtered(lambda l: l.state in ('pending', 'in_progress')))
            record.failed_tasks = len(lines.filtered(lambda l: l.state == 'failed'))

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise ValidationError(_('La fecha de inicio debe ser anterior a la fecha de fin.'))

    def action_start_closing(self):
        """Iniciar el proceso de cierre"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Solo se puede iniciar el cierre desde estado Borrador.'))
        
        # Verificar que hay tareas
        if not self.line_ids:
            raise UserError(_('No hay tareas definidas para este cierre. Verifique la plantilla.'))
        
        self.state = 'in_progress'
        self.message_post(
            body=_('Proceso de cierre iniciado.'),
            subject=_('Cierre Iniciado')
        )

    def action_send_to_review(self):
        """Enviar a revisión"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_('Solo se puede enviar a revisión desde estado En Progreso.'))
        
        # Verificar tareas obligatorias
        required_pending = self.line_ids.filtered(
            lambda l: l.required and l.state not in ('done', 'skipped')
        )
        if required_pending:
            raise UserError(_(
                'No se puede enviar a revisión. Las siguientes tareas obligatorias están pendientes:\n%s'
            ) % '\n'.join(required_pending.mapped('name')))
        
        self.state = 'to_review'
        self.message_post(
            body=_('Cierre enviado a revisión.'),
            subject=_('Enviado a Revisión')
        )

    def action_approve_closing(self):
        """Aprobar y cerrar el período"""
        self.ensure_one()
        if self.state != 'to_review':
            raise UserError(_('Solo se puede aprobar desde estado A Revisar.'))
        
        # Verificar permisos
        if not self.env.user.has_group('account.group_account_manager'):
            raise UserError(_('Solo los Gerentes Contables pueden aprobar cierres.'))
        
        # Verificar que todas las tareas obligatorias estén completadas
        required_pending = self.line_ids.filtered(
            lambda l: l.required and l.state not in ('done', 'skipped')
        )
        if required_pending:
            raise UserError(_(
                'No se puede aprobar el cierre. Las siguientes tareas obligatorias están pendientes:\n%s'
            ) % '\n'.join(required_pending.mapped('name')))
        
        # Establecer fechas de bloqueo
        self._set_lock_dates()
        
        # Actualizar estado
        self.write({
            'state': 'done',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now()
        })
        
        self.message_post(
            body=_('Cierre aprobado y período bloqueado hasta %s.') % self.date_to,
            subject=_('Cierre Aprobado')
        )

    def action_reopen_closing(self):
        """Reabrir el cierre"""
        self.ensure_one()
        if self.state != 'done':
            raise UserError(_('Solo se pueden reabrir cierres en estado Cerrado.'))
        
        # Verificar permisos
        if not self.env.user.has_group('account.group_account_manager'):
            raise UserError(_('Solo los Gerentes Contables pueden reabrir cierres.'))
        
        # Obtener motivo (esto se debería hacer desde un wizard, pero por simplicidad lo dejamos así)
        self.state = 'in_progress'
        
        self.message_post(
            body=_('Cierre reabierto por %s. ATENCIÓN: Las fechas de bloqueo contable deben ajustarse manualmente.') % self.env.user.name,
            subject=_('Cierre Reabierto')
        )

    def action_cancel_closing(self):
        """Cancelar el cierre"""
        self.ensure_one()
        if self.state == 'done':
            raise UserError(_('No se puede cancelar un cierre aprobado. Use "Reabrir" en su lugar.'))
        
        self.state = 'cancel'
        self.message_post(
            body=_('Cierre cancelado.'),
            subject=_('Cierre Cancelado')
        )

    def _get_available_lock_fields(self):
        """Obtener los campos de bloqueo disponibles en account.change.lock.date"""
        try:
            # Verificar si el modelo account.change.lock.date existe
            if 'account.change.lock.date' in self.env:
                lock_model = self.env['account.change.lock.date']
                lock_fields = {}
                
                # Verificar campos disponibles en el modelo
                model_fields = lock_model._fields
                
                if 'sale_lock_date' in model_fields:
                    lock_fields['sales'] = 'sale_lock_date'
                
                if 'purchase_lock_date' in model_fields:
                    lock_fields['purchases'] = 'purchase_lock_date'
                
                if 'tax_lock_date' in model_fields:
                    lock_fields['tax'] = 'tax_lock_date'
                
                _logger.info('Campos de bloqueo disponibles en account.change.lock.date: %s', lock_fields)
                return lock_fields
            else:
                _logger.warning('Modelo account.change.lock.date no disponible')
                return {}
                
        except Exception as e:
            _logger.error('Error al verificar campos de bloqueo: %s', str(e))
            return {}

    def _set_lock_dates(self):
        """Establecer las fechas de bloqueo contable y fiscal usando account.change.lock.date"""
        self.ensure_one()
        
        try:
            lock_fields = self._get_available_lock_fields()
            
            if not lock_fields:
                _logger.warning('No se encontraron campos de bloqueo disponibles')
                self.lock_date_set = False
                self.tax_lock_date_set = False
                return
            
            # Crear o buscar un registro de cambio de fecha de bloqueo
            lock_model = self.env['account.change.lock.date']
            
            # Valores a establecer
            lock_values = {}
            
            # Establecer fecha de bloqueo de ventas
            if 'sales' in lock_fields:
                lock_values['sale_lock_date'] = self.date_to
                self.lock_date_set = self.date_to
                _logger.info('Fecha de bloqueo de ventas establecida: %s', self.date_to)
            
            # Establecer fecha de bloqueo de compras
            if 'purchases' in lock_fields:
                lock_values['purchase_lock_date'] = self.date_to
                _logger.info('Fecha de bloqueo de compras establecida: %s', self.date_to)
            
            # Establecer fecha de bloqueo fiscal
            if 'tax' in lock_fields:
                lock_values['tax_lock_date'] = self.date_to
                self.tax_lock_date_set = self.date_to
                _logger.info('Fecha de bloqueo fiscal establecida: %s', self.date_to)
            
            # Crear el registro de cambio de bloqueo si hay valores que establecer
            if lock_values:
                lock_record = lock_model.create(lock_values)
                
                # Ejecutar la acción de cambio de fecha de bloqueo
                # Esto aplicará los cambios a la compañía
                if hasattr(lock_record, 'change_lock_date'):
                    lock_record.change_lock_date()
                    _logger.info('Fechas de bloqueo aplicadas exitosamente a la compañía')
                elif hasattr(lock_record, 'action_change_lock_date'):
                    lock_record.action_change_lock_date()
                    _logger.info('Fechas de bloqueo aplicadas exitosamente a la compañía')
                else:
                    _logger.warning('No se encontró método para aplicar las fechas de bloqueo')
            else:
                _logger.warning('No hay valores de bloqueo para establecer')
                self.lock_date_set = False
                self.tax_lock_date_set = False
                        
        except Exception as e:
            _logger.error('Error al establecer fechas de bloqueo: %s', str(e))
            # En lugar de fallar completamente, hacer el cierre sin bloqueo
            self.lock_date_set = False
            self.tax_lock_date_set = False
            self.message_post(
                body=_(
                    'Advertencia: No se pudieron establecer las fechas de bloqueo automáticamente. '
                    'Error: %s\n\nEl cierre se completó pero debe establecer manualmente las fechas '
                    'de bloqueo en Contabilidad > Configuración > Fechas de Bloqueo.'
                ) % str(e),
                subject=_('Advertencia: Fechas de Bloqueo')
            )

    def action_view_tasks_kanban(self):
        """Abrir las tareas en vista kanban"""
        self.ensure_one()
        return {
            'name': _('Tareas de Cierre - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'closing.worksheet.line',
            'view_mode': 'kanban,list,form',
            'domain': [('worksheet_id', '=', self.id)],
            'context': {
                'default_worksheet_id': self.id,
                'group_by': 'state'
            },
            'target': 'current',
        }

    def action_view_closing_report(self):
        """Acción para ver el reporte de cierre"""
        self.ensure_one()
        return self.env.ref('account_closing_control.action_report_closing_worksheet').report_action(self)

    @api.model_create_multi
    def create(self, vals_list):
        """Override create para generar automáticamente las líneas desde la plantilla"""
        records = super().create(vals_list)
        for record in records:
            if record.template_id and not record.line_ids:
                record._create_lines_from_template()
        return records

    def _create_lines_from_template(self):
        """Crear las líneas de la hoja de cierre desde la plantilla"""
        self.ensure_one()
        if not self.template_id:
            return
        
        lines_data = []
        for template_line in self.template_id.line_ids:
            lines_data.append({
                'worksheet_id': self.id,
                'name': template_line.name,
                'description': template_line.description,
                'sequence': template_line.sequence,
                'validation_type': template_line.validation_type,
                'related_action_id': template_line.related_action_id.id if template_line.related_action_id else False,
                'python_code': template_line.python_code,
                'required': template_line.required,
                'responsible_group_id': template_line.responsible_group_id.id if template_line.responsible_group_id else False,
                'state': 'pending'
            })
        
        self.env['closing.worksheet.line'].create(lines_data)


class ClosingWorksheetLine(models.Model):
    _name = 'closing.worksheet.line'
    _description = 'Tarea de Cierre Contable'
    _order = 'sequence, id'

    worksheet_id = fields.Many2one(
        'closing.worksheet',
        string='Hoja de Cierre',
        required=True,
        ondelete='cascade'
    )
    
    name = fields.Char(
        string='Tarea',
        required=True
    )
    
    description = fields.Html(
        string='Instrucciones'
    )
    
    sequence = fields.Integer(
        string='Secuencia',
        default=10
    )
    
    validation_type = fields.Selection([
        ('manual', 'Manual'),
        ('action', 'Acción'),
        ('python', 'Python')
    ], string='Tipo', required=True)
    
    related_action_id = fields.Many2one(
        'ir.actions.act_window',
        string='Acción'
    )
    
    python_code = fields.Text(
        string='Código Python'
    )
    
    required = fields.Boolean(
        string='Obligatorio',
        default=True
    )
    
    responsible_group_id = fields.Many2one(
        'res.groups',
        string='Grupo Responsable'
    )
    
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('in_progress', 'En Progreso'),
        ('done', 'Completado'),
        ('failed', 'Fallido'),
        ('skipped', 'Omitido')
    ], string='Estado', default='pending', required=True)
    
    user_id = fields.Many2one(
        'res.users',
        string='Responsable'
    )
    
    notes = fields.Html(
        string='Notas',
        help='Comentarios del analista'
    )
    
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Adjuntos',
        help='Papeles de trabajo adjuntos'
    )
    
    validation_log = fields.Text(
        string='Log de Validación',
        readonly=True,
        help='Resultado de la validación automática'
    )
    
    completed_date = fields.Datetime(
        string='Fecha de Finalización',
        readonly=True
    )
    
    completed_by = fields.Many2one(
        'res.users',
        string='Completado por',
        readonly=True
    )

    def action_mark_done(self):
        """Marcar tarea como completada (validación manual)"""
        for record in self:
            if record.validation_type != 'manual':
                raise UserError(_('Solo las tareas manuales se pueden marcar como completadas directamente.'))
            
            record.write({
                'state': 'done',
                'user_id': self.env.user.id,
                'completed_date': fields.Datetime.now(),
                'completed_by': self.env.user.id
            })

    def action_execute_action(self):
        """Ejecutar la acción relacionada"""
        self.ensure_one()
        if self.validation_type != 'action' or not self.related_action_id:
            raise UserError(_('Esta tarea no tiene una acción configurada.'))
        
        # Marcar como en progreso
        self.state = 'in_progress'
        self.user_id = self.env.user.id
        
        # Ejecutar la acción
        action = self.related_action_id.read()[0]
        action['target'] = 'new'  # Abrir en ventana modal
        return action

    def action_validate_python(self):
        """Ejecutar validación Python"""
        self.ensure_one()
        if self.validation_type != 'python' or not self.python_code:
            raise UserError(_('Esta tarea no tiene código Python configurado.'))
        
        try:
            # Marcar como en progreso
            self.state = 'in_progress'
            self.user_id = self.env.user.id
            
            # Preparar contexto de ejecución
            local_vars = {
                'self': self,
                'env': self.env,
                'worksheet': self.worksheet_id,
                'company': self.worksheet_id.company_id,
                'date_from': self.worksheet_id.date_from,
                'date_to': self.worksheet_id.date_to,
                'UserError': UserError,
                'ValidationError': ValidationError,
                '_': _,
                'datetime': datetime,
                'date': date,
                'fields': fields
            }
            
            # Ejecutar el código
            exec(self.python_code, {}, local_vars)
            
            # Si llegamos aquí, la validación fue exitosa
            self.write({
                'state': 'done',
                'validation_log': _('Validación exitosa ejecutada el %s') % fields.Datetime.now(),
                'completed_date': fields.Datetime.now(),
                'completed_by': self.env.user.id
            })
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Validación Exitosa'),
                    'message': _('La validación se ejecutó correctamente.'),
                    'type': 'success'
                }
            }
            
        except Exception as e:
            # La validación falló
            error_msg = str(e)
            self.write({
                'state': 'failed',
                'validation_log': _('Error en validación: %s') % error_msg
            })
            
            raise UserError(_(
                'La validación falló:\n%s\n\n'
                'Revise el código Python o corrija los problemas identificados.'
            ) % error_msg)

    def action_skip_task(self):
        """Omitir tarea (solo para tareas no obligatorias)"""
        self.ensure_one()
        if self.required:
            raise UserError(_('No se pueden omitir tareas obligatorias.'))
        
        self.write({
            'state': 'skipped',
            'user_id': self.env.user.id,
            'completed_date': fields.Datetime.now(),
            'completed_by': self.env.user.id
        })

    def action_reset_task(self):
        """Reiniciar tarea a estado pendiente"""
        self.ensure_one()
        self.write({
            'state': 'pending',
            'user_id': False,
            'validation_log': False,
            'completed_date': False,
            'completed_by': False
        })

    @api.model
    def _group_expand_states(self, states, domain, order):
        """Expandir todos los estados para el kanban"""
        return [key for key, val in type(self).state.selection]