from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class InternalTransferWizard(models.TransientModel):
    _name = 'internal.transfer.wizard'
    _description = 'Wizard intuitivo para transferencias internas entre diarios'

    # Información de origen
    source_journal_id = fields.Many2one(
        'account.journal',
        string='Diario Origen',
        required=True,
        domain="[('type', 'in', ('bank', 'cash'))]"
    )
    
    source_journal_name = fields.Char(
        string='Nombre Origen',
        related='source_journal_id.name',
        readonly=True
    )
    
    source_currency_id = fields.Many2one(
        'res.currency',
        string='Moneda Origen',
        related='source_journal_id.currency_id',
        readonly=True
    )
    
    source_company_currency = fields.Boolean(
        string='Es moneda de la empresa (origen)',
        compute='_compute_currency_flags',
        readonly=True
    )
    
    # Información de destino
    destination_journal_id = fields.Many2one(
        'account.journal',
        string='Diario Destino',
        required=True,
        domain="[('type', 'in', ('bank', 'cash')), ('id', '!=', source_journal_id)]"
    )
    
    destination_journal_name = fields.Char(
        string='Nombre Destino',
        related='destination_journal_id.name',
        readonly=True
    )
    
    destination_currency_id = fields.Many2one(
        'res.currency',
        string='Moneda Destino',
        related='destination_journal_id.currency_id',
        readonly=True
    )
    
    destination_company_currency = fields.Boolean(
        string='Es moneda de la empresa (destino)',
        compute='_compute_currency_flags',
        readonly=True
    )
    
    # Datos de la transferencia
    amount = fields.Monetary(
        string='Monto a transferir',
        required=True,
        currency_field='transfer_currency_id'
    )
    
    # Campo para el monto en moneda de la empresa (editable)
    amount_company_currency = fields.Monetary(
        string='Total a transferir en moneda empresa',
        currency_field='company_currency_id',
        help="Monto total en la moneda de la empresa. Al modificar este campo se recalculará el tipo de cambio."
    )
    
    # Campo para la moneda de la empresa
    company_currency_id = fields.Many2one(
        'res.currency',
        string='Moneda empresa',
        related='company_id.currency_id',
        readonly=True
    )
    
    # Campo para la empresa
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        default=lambda self: self.env.company,
        readonly=True
    )
    
    transfer_currency_id = fields.Many2one(
        'res.currency',
        string='Moneda de transferencia',
        required=True,
        help="Seleccione la moneda en la que desea realizar la transferencia"
    )
    
    # Campo para mostrar claramente qué divisa se transfiere
    transfer_currency_name = fields.Char(
        string='Divisa a transferir',
        related='transfer_currency_id.name',
        readonly=True,
        help="Esta es la moneda que recibirá el diario de destino"
    )
    
    # Campo para mostrar el tipo de transferencia
    transfer_type_description = fields.Char(
        string='Tipo de transferencia',
        compute='_compute_transfer_type_description',
        readonly=True
    )
    
    # Campo para las monedas disponibles en el dominio
    available_currency_ids = fields.Many2many(
        'res.currency',
        compute='_compute_available_currencies',
        help="Monedas disponibles para la transferencia"
    )
    
    date = fields.Date(
        string='Fecha',
        required=True,
        default=fields.Date.context_today
    )
    
    memo = fields.Char(
        string='Descripción',
        default='Transferencia interna'
    )
    
    # Información visual
    is_multicurrency = fields.Boolean(
        string='Es transferencia multicurrency',
        compute='_compute_currency_flags',
        readonly=True
    )
    
    exchange_rate = fields.Float(
        string='Tipo de cambio',
        digits=(12, 6),
        help="Solo para transferencias entre diferentes monedas"
    )
    
    show_exchange_rate = fields.Boolean(
        string='Mostrar tipo de cambio',
        compute='_compute_currency_flags'
    )

    @api.depends('source_journal_id', 'destination_journal_id')
    def _compute_currency_flags(self):
        for wizard in self:
            company_currency = wizard.env.company.currency_id
            
            # Determinar si las monedas son de la empresa
            wizard.source_company_currency = not wizard.source_currency_id or wizard.source_currency_id == company_currency
            wizard.destination_company_currency = not wizard.destination_currency_id or wizard.destination_currency_id == company_currency
            
            # Es multicurrency si las monedas son diferentes
            source_curr = wizard.source_currency_id or company_currency
            dest_curr = wizard.destination_currency_id or company_currency
            wizard.is_multicurrency = source_curr != dest_curr
            wizard.show_exchange_rate = wizard.is_multicurrency

    @api.depends('source_journal_id', 'destination_journal_id')
    def _compute_available_currencies(self):
        """Compute available currencies for transfer"""
        for wizard in self:
            company_currency = wizard.env.company.currency_id
            currencies = wizard.env['res.currency'].search([])
            
            if wizard.source_journal_id and wizard.destination_journal_id:
                source_curr = wizard.source_currency_id or company_currency
                dest_curr = wizard.destination_currency_id or company_currency
                
                # Incluir ambas monedas de los diarios más la moneda de la empresa
                available_currencies = source_curr | dest_curr | company_currency
                
                wizard.available_currency_ids = available_currencies
            else:
                wizard.available_currency_ids = currencies
    
    @api.depends('transfer_currency_id', 'source_journal_id', 'destination_journal_id')
    def _compute_transfer_type_description(self):
        """Compute transfer type description based on selected currency"""
        for wizard in self:
            if not wizard.transfer_currency_id:
                wizard.transfer_type_description = ""
                continue
                
            company_currency = wizard.env.company.currency_id
            source_curr = wizard.source_currency_id or company_currency
            dest_curr = wizard.destination_currency_id or company_currency
            transfer_curr = wizard.transfer_currency_id
            
            if transfer_curr == source_curr == dest_curr:
                wizard.transfer_type_description = f"Transferencia directa en {transfer_curr.name}"
            elif transfer_curr == source_curr and transfer_curr != dest_curr:
                wizard.transfer_type_description = f"Transferir {transfer_curr.name} (destino recibirá {transfer_curr.name})"
            elif transfer_curr == dest_curr and transfer_curr != source_curr:
                wizard.transfer_type_description = f"Convertir de {source_curr.name} a {transfer_curr.name}"
            elif transfer_curr == company_currency:
                wizard.transfer_type_description = f"Transferencia en moneda empresa ({transfer_curr.name})"
            else:
                wizard.transfer_type_description = f"Transferencia en {transfer_curr.name}"
    
    @api.onchange('source_journal_id', 'destination_journal_id')
    def _onchange_journals(self):
        """Set default transfer currency when journals change"""
        if self.source_journal_id and self.destination_journal_id:
            company_currency = self.env.company.currency_id
            source_curr = self.source_currency_id or company_currency
            dest_curr = self.destination_currency_id or company_currency
            
            # Lógica por defecto: si origen tiene moneda extranjera, usarla
            if source_curr != company_currency:
                self.transfer_currency_id = source_curr
            else:
                self.transfer_currency_id = dest_curr
            
            # Recalcular tipo de cambio y monto empresa
            self._recalculate_exchange_rate()
            self._recalculate_company_amount()
        else:
            self.transfer_currency_id = False
            self.amount_company_currency = 0.0

    @api.onchange('source_journal_id')
    def _onchange_source_journal(self):
        """Limpiar destino cuando cambia origen"""
        if self.destination_journal_id and self.destination_journal_id.id == self.source_journal_id.id:
            self.destination_journal_id = False

    @api.onchange('destination_journal_id')
    def _onchange_destination_journal(self):
        """Calcular tipo de cambio automáticamente si es necesario"""
        if self.is_multicurrency and self.source_currency_id and self.destination_currency_id:
            # Obtener tipo de cambio actual del origen a la moneda de la empresa
            company_currency = self.env.company.currency_id
            source_curr = self.source_currency_id or company_currency
            
            if source_curr != company_currency:
                rate = source_curr._get_conversion_rate(
                    source_curr,
                    company_currency,
                    self.env.company,
                    self.date or fields.Date.today()
                )
                self.exchange_rate = rate
            else:
                self.exchange_rate = 1.0

    @api.onchange('date')
    def _onchange_date(self):
        """Recalcular tipo de cambio cuando cambia la fecha"""
        if self.is_multicurrency and self.transfer_currency_id:
            self._recalculate_exchange_rate()
            self._recalculate_company_amount()

    @api.onchange('amount', 'transfer_currency_id', 'exchange_rate')
    def _onchange_amount_or_currency(self):
        """Recalcular monto en moneda empresa cuando cambia el monto o la moneda"""
        self._recalculate_company_amount()
    
    @api.onchange('amount_company_currency')
    def _onchange_company_amount(self):
        """Recalcular tipo de cambio cuando cambia el monto en moneda empresa"""
        if self.amount_company_currency and self.amount and self.transfer_currency_id:
            company_currency = self.env.company.currency_id
            
            if self.transfer_currency_id != company_currency:
                # Recalcular tipo de cambio: amount_company / amount_foreign
                if self.amount > 0:
                    new_rate = self.amount_company_currency / self.amount
                    self.exchange_rate = new_rate
                    _logger.info(f"Tipo de cambio recalculado por monto empresa: {new_rate}")
    
    def _recalculate_exchange_rate(self):
        """Recalcular tipo de cambio basado en la fecha y monedas"""
        if self.transfer_currency_id and self.date:
            company_currency = self.env.company.currency_id
            
            if self.transfer_currency_id != company_currency:
                rate = self.transfer_currency_id._get_conversion_rate(
                    self.transfer_currency_id,
                    company_currency,
                    self.env.company,
                    self.date
                )
                self.exchange_rate = rate
            else:
                self.exchange_rate = 1.0
    
    def _recalculate_company_amount(self):
        """Recalcular monto en moneda empresa basado en el monto y tipo de cambio"""
        if self.amount and self.transfer_currency_id:
            company_currency = self.env.company.currency_id
            
            if self.transfer_currency_id == company_currency:
                # Misma moneda
                self.amount_company_currency = self.amount
            else:
                # Diferente moneda - usar tipo de cambio
                if self.exchange_rate and self.exchange_rate > 0:
                    self.amount_company_currency = self.amount * self.exchange_rate
                else:
                    # Si no hay tipo de cambio, calcularlo
                    self._recalculate_exchange_rate()
                    if self.exchange_rate and self.exchange_rate > 0:
                        self.amount_company_currency = self.amount * self.exchange_rate

    def action_create_transfer(self):
        """Crear la transferencia interna con manejo correcto de multi-moneda"""
        self.ensure_one()
        
        _logger.info("=== INICIO TRANSFERENCIA INTERNA ===")
        _logger.info(f"Diario origen: {self.source_journal_id.name} (ID: {self.source_journal_id.id})")
        _logger.info(f"Diario destino: {self.destination_journal_id.name} (ID: {self.destination_journal_id.id})")
        _logger.info(f"Monto: {self.amount}")
        _logger.info(f"Tipo de cambio: {self.exchange_rate}")
        
        if not self.source_journal_id or not self.destination_journal_id:
            raise ValidationError(_('Debe seleccionar diarios de origen y destino.'))
        
        if self.source_journal_id == self.destination_journal_id:
            raise ValidationError(_('Los diarios de origen y destino deben ser diferentes.'))
        
        if self.amount <= 0:
            raise ValidationError(_('El monto debe ser mayor a cero.'))
        
        try:
            # Obtener monedas
            company_currency = self.env.company.currency_id
            source_currency = self.source_currency_id or company_currency
            dest_currency = self.destination_currency_id or company_currency
            
            _logger.info(f"Moneda empresa: {company_currency.name}")
            _logger.info(f"Moneda origen: {source_currency.name}")
            _logger.info(f"Moneda destino: {dest_currency.name}")
            _logger.info(f"Es multi-moneda: {source_currency != dest_currency}")
            
            # Si es transferencia de la misma moneda, usar el módulo estándar con pareado
            if source_currency == dest_currency and (not self.transfer_currency_id or self.transfer_currency_id == source_currency):
                _logger.info("*** TRANSFERENCIA MISMA MONEDA ***")
                payment_vals = {
                    'payment_type': 'outbound',
                    'journal_id': self.source_journal_id.id,
                    'destination_journal_id': self.destination_journal_id.id,
                    'amount': self.amount,
                    'currency_id': self.transfer_currency_id.id if self.transfer_currency_id else source_currency.id,
                    'date': self.date,
                    'memo': self.memo or _('Transferencia interna'),
                    'is_internal_transfer': True,
                    'partner_id': False,
                }
                
                _logger.info(f"Valores del pago: {payment_vals}")
                payment = self.env['account.payment'].create(payment_vals)
                _logger.info(f"Pago creado ID: {payment.id}")
                payment.action_post()
                _logger.info("Pago publicado exitosamente")
                
                return {
                    'name': _('Transferencia Interna Creada'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.payment',
                    'res_id': payment.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
            
            # Para transferencias multi-moneda, manejar correctamente la moneda de transferencia
            else:
                _logger.info("*** TRANSFERENCIA MULTI-MONEDA CON PAREADO ***")
                
                # Verificar la cuenta de transferencia de la empresa
                transfer_account = self.env.company.transfer_account_id
                _logger.info(f"Cuenta de transferencia: {transfer_account.code} - {transfer_account.name}")
                _logger.info(f"Moneda secundaria de cuenta transferencia: {transfer_account.currency_id.name if transfer_account.currency_id else 'No definida'}")
                
                # Calcular tipos de cambio
                if self.exchange_rate and self.exchange_rate > 0:
                    rate = self.exchange_rate
                    _logger.info(f"Usando tipo de cambio del formulario: {rate}")
                else:
                    rate = source_currency._get_conversion_rate(
                        source_currency,
                        company_currency,
                        self.env.company,
                        self.date
                    )
                    _logger.info(f"Usando tipo de cambio del sistema: {rate}")
                
                _logger.info(f"Moneda empresa: {company_currency.name}")
                _logger.info(f"Moneda origen: {source_currency.name}")
                _logger.info(f"Moneda destino: {dest_currency.name}")
                _logger.info(f"Tipo de cambio: {rate}")
                
                # LÓGICA CORREGIDA: Usar la moneda seleccionada por el usuario
                transfer_currency = self.transfer_currency_id
                transfer_amount = self.amount
                
                _logger.info(f"Moneda seleccionada por usuario: {transfer_currency.name}")
                _logger.info(f"Monto a transferir: {transfer_amount}")
                
                # Crear la transferencia con la moneda seleccionada por el usuario
                payment_vals = {
                    'payment_type': 'outbound',
                    'journal_id': self.source_journal_id.id,
                    'destination_journal_id': self.destination_journal_id.id,
                    'amount': transfer_amount,
                    'currency_id': transfer_currency.id,  # Usar la moneda seleccionada por el usuario
                    'date': self.date,
                    'memo': self.memo or _('Transferencia interna multi-moneda'),
                    'is_internal_transfer': True,
                    'partner_id': False,
                }
                
                _logger.info(f"Valores del pago multi-moneda: {payment_vals}")
                _logger.info(f"Moneda de transferencia final: {transfer_currency.name}")
                
                payment = self.env['account.payment'].create(payment_vals)
                _logger.info(f"Pago multi-moneda creado ID: {payment.id}")
                payment.action_post()
                _logger.info("Transferencia multi-moneda publicada exitosamente")
                
                main_payment = payment
                
                _logger.info(f"=== TRANSFERENCIA COMPLETADA - Pago principal ID: {main_payment.id} ===")
                
                return {
                    'name': _('Transferencia Multi-moneda Creada'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.payment',
                    'res_id': main_payment.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
            
        except Exception as e:
            _logger.error(f"ERROR en transferencia interna: {str(e)}")
            _logger.exception("Detalles del error:")
            raise ValidationError(_(
                'Error al crear la transferencia interna: %s\n\n'
                'Verifique que:\n'
                '- Los diarios tengan configuradas las cuentas correspondientes\n'
                '- Los métodos de pago estén correctamente configurados\n'
                '- Las monedas estén correctamente configuradas'
            ) % str(e))