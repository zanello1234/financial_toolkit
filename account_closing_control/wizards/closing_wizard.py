# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import calendar


class ClosingWizard(models.TransientModel):
    _name = 'closing.wizard'
    _description = 'Asistente para Crear Hoja de Cierre'

    template_id = fields.Many2one(
        'closing.template',
        string='Plantilla de Cierre',
        required=True,
        domain="[('company_id', '=', company_id)]"
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company
    )
    
    periodicity = fields.Selection(
        related='template_id.periodicity',
        readonly=True,
        string='Periodicidad'
    )
    
    # Campos para período manual
    date_from = fields.Date(
        string='Fecha Inicio',
        required=True
    )
    
    date_to = fields.Date(
        string='Fecha Fin',
        required=True
    )
    
    # Campos para selección rápida de período
    year = fields.Integer(
        string='Año',
        required=True,
        default=lambda self: datetime.now().year
    )
    
    month = fields.Selection([
        ('1', 'Enero'), ('2', 'Febrero'), ('3', 'Marzo'),
        ('4', 'Abril'), ('5', 'Mayo'), ('6', 'Junio'),
        ('7', 'Julio'), ('8', 'Agosto'), ('9', 'Septiembre'),
        ('10', 'Octubre'), ('11', 'Noviembre'), ('12', 'Diciembre')
    ], string='Mes')
    
    quarter = fields.Selection([
        ('1', 'Q1 (Ene-Mar)'),
        ('2', 'Q2 (Abr-Jun)'),
        ('3', 'Q3 (Jul-Sep)'),
        ('4', 'Q4 (Oct-Dic)')
    ], string='Trimestre')
    
    period_selection_mode = fields.Selection([
        ('quick', 'Selección Rápida'),
        ('manual', 'Fechas Manuales')
    ], string='Modo de Selección', default='quick', required=True)
    
    name = fields.Char(
        string='Nombre del Cierre',
        compute='_compute_name',
        store=True,
        readonly=False,
        help='Se genera automáticamente pero se puede modificar'
    )
    
    existing_worksheet_ids = fields.Many2many(
        'closing.worksheet',
        string='Cierres Existentes',
        compute='_compute_existing_worksheets',
        help='Cierres existentes para el período seleccionado'
    )
    
    has_existing_worksheets = fields.Boolean(
        string='Tiene Cierres Existentes',
        compute='_compute_existing_worksheets'
    )

    @api.depends('template_id', 'year', 'month', 'quarter', 'date_from', 'date_to', 'period_selection_mode')
    def _compute_name(self):
        for record in self:
            if not record.template_id:
                record.name = ''
                continue
            
            try:
                if record.period_selection_mode == 'quick':
                    if record.template_id.periodicity == 'monthly' and record.month:
                        month_name = dict(record._fields['month'].selection)[record.month]
                        record.name = f"{record.template_id.name} {month_name} {record.year}"
                    elif record.template_id.periodicity == 'quarterly' and record.quarter:
                        quarter_name = dict(record._fields['quarter'].selection)[record.quarter]
                        record.name = f"{record.template_id.name} {quarter_name} {record.year}"
                    elif record.template_id.periodicity == 'annual':
                        record.name = f"{record.template_id.name} {record.year}"
                    else:
                        record.name = f"{record.template_id.name} {record.year}"
                else:
                    # Modo manual
                    if record.date_from and record.date_to:
                        record.name = f"{record.template_id.name} {record.date_from.strftime('%d/%m/%Y')} - {record.date_to.strftime('%d/%m/%Y')}"
                    else:
                        record.name = record.template_id.name
            except:
                record.name = record.template_id.name if record.template_id else ''

    @api.depends('date_from', 'date_to', 'template_id')
    def _compute_existing_worksheets(self):
        for record in self:
            if record.date_from and record.date_to and record.template_id:
                # Buscar cierres existentes que se solapen con el período
                existing = self.env['closing.worksheet'].search([
                    ('template_id', '=', record.template_id.id),
                    ('company_id', '=', record.company_id.id),
                    ('state', '!=', 'cancel'),
                    '|',
                    '&', ('date_from', '<=', record.date_from), ('date_to', '>=', record.date_from),
                    '&', ('date_from', '<=', record.date_to), ('date_to', '>=', record.date_to)
                ])
                record.existing_worksheet_ids = existing
                record.has_existing_worksheets = bool(existing)
            else:
                record.existing_worksheet_ids = False
                record.has_existing_worksheets = False

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id:
            # Ajustar campos visibles según periodicidad
            self.month = False
            self.quarter = False
            
            # Establecer período por defecto
            now = datetime.now()
            if self.template_id.periodicity == 'monthly':
                # Mes anterior
                last_month = now.replace(day=1) - relativedelta(days=1)
                self.month = str(last_month.month)
                self.year = last_month.year
            elif self.template_id.periodicity == 'quarterly':
                # Trimestre anterior
                current_quarter = (now.month - 1) // 3 + 1
                if current_quarter == 1:
                    self.quarter = '4'
                    self.year = now.year - 1
                else:
                    self.quarter = str(current_quarter - 1)
                    self.year = now.year
            else:  # annual
                self.year = now.year - 1

    @api.onchange('year', 'month', 'quarter', 'template_id', 'period_selection_mode')
    def _onchange_period_quick(self):
        if self.period_selection_mode == 'quick' and self.template_id:
            try:
                if self.template_id.periodicity == 'monthly' and self.month and self.year:
                    month_num = int(self.month)
                    # Primer día del mes
                    self.date_from = date(self.year, month_num, 1)
                    # Último día del mes
                    last_day = calendar.monthrange(self.year, month_num)[1]
                    self.date_to = date(self.year, month_num, last_day)
                    
                elif self.template_id.periodicity == 'quarterly' and self.quarter and self.year:
                    quarter_num = int(self.quarter)
                    # Calcular primer mes del trimestre
                    first_month = (quarter_num - 1) * 3 + 1
                    self.date_from = date(self.year, first_month, 1)
                    # Último día del último mes del trimestre
                    last_month = first_month + 2
                    if last_month <= 12:
                        last_day = calendar.monthrange(self.year, last_month)[1]
                        self.date_to = date(self.year, last_month, last_day)
                    else:
                        # Diciembre
                        self.date_to = date(self.year, 12, 31)
                        
                elif self.template_id.periodicity == 'annual' and self.year:
                    self.date_from = date(self.year, 1, 1)
                    self.date_to = date(self.year, 12, 31)
            except:
                pass

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to and record.date_from > record.date_to:
                raise ValidationError(_('La fecha de inicio debe ser anterior a la fecha de fin.'))

    def action_create_worksheet(self):
        """Crear la hoja de cierre"""
        self.ensure_one()
        
        # Validaciones
        if not self.template_id:
            raise UserError(_('Debe seleccionar una plantilla de cierre.'))
        
        if not self.date_from or not self.date_to:
            raise UserError(_('Debe especificar las fechas del período.'))
        
        if not self.name:
            raise UserError(_('Debe especificar un nombre para el cierre.'))
        
        # Verificar si ya existe un cierre para este período
        if self.has_existing_worksheets:
            existing_names = ', '.join(self.existing_worksheet_ids.mapped('name'))
            raise UserError(_(
                'Ya existen cierres para este período:\n%s\n\n'
                'No se pueden crear cierres superpuestos. '
                'Modifique las fechas o cancele los cierres existentes.'
            ) % existing_names)
        
        # Verificar que la plantilla tenga líneas
        if not self.template_id.line_ids:
            raise UserError(_(
                'La plantilla seleccionada no tiene tareas configuradas.\n'
                'Configure las tareas en la plantilla antes de crear el cierre.'
            ))
        
        try:
            # Crear la hoja de cierre
            worksheet_vals = {
                'name': self.name,
                'template_id': self.template_id.id,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'company_id': self.company_id.id,
                'state': 'draft'
            }
            
            worksheet = self.env['closing.worksheet'].create(worksheet_vals)
            
            # Las líneas se crean automáticamente en el create del worksheet
            
            # Retornar acción para abrir la hoja de cierre creada
            return {
                'type': 'ir.actions.act_window',
                'name': _('Hoja de Cierre Creada'),
                'res_model': 'closing.worksheet',
                'res_id': worksheet.id,
                'view_mode': 'form',
                'target': 'current',
                'context': {'form_view_initial_mode': 'edit'}
            }
            
        except Exception as e:
            raise UserError(_(
                'Error al crear la hoja de cierre:\n%s\n\n'
                'Verifique la configuración de la plantilla y los permisos.'
            ) % str(e))

    def action_view_existing_worksheets(self):
        """Ver cierres existentes para el período"""
        self.ensure_one()
        
        if not self.existing_worksheet_ids:
            raise UserError(_('No hay cierres existentes para mostrar.'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cierres Existentes'),
            'res_model': 'closing.worksheet',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.existing_worksheet_ids.ids)],
            'target': 'new'
        }