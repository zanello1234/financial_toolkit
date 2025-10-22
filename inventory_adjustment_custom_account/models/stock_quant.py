# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.tools.float_utils import float_is_zero
import logging # Importar logging

_logger = logging.getLogger(__name__) # Inicializar logger

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    # --- Definición del Campo ---
    x_adjustment_account_id = fields.Many2one(
        'account.account',
        string='Adjustment Account',
        company_dependent=True,
        copy=False,
        help="Select a specific account for the inventory adjustment journal entry."
             " If left empty, the default account from the inventory adjustment location will be used."
    )

    # --- Lógica Principal: Aplicar Inventario y Pasar Contexto ---
    # Heredamos _apply_inventory para pasar la cuenta en contexto,
    # el objetivo es que lo use el stock.move al crear la capa
    def _apply_inventory(self):
        # Log al inicio del método
        _logger.info(f"--- Inicio _apply_inventory para Quants: {self.ids} ---")

        # Iteramos sobre los quants para construir el mapa y loggear la información
        quant_account_map = {}
        for quant in self:
             # Log individual para ver qué cuenta se seleccionó (si alguna)
             _logger.info(f"Procesando Quant ID: {quant.id}, Producto: {quant.product_id.display_name}, Cantidad Contada: {quant.inventory_quantity}, Cuenta Ajuste Seleccionada: {quant.x_adjustment_account_id.id} ({quant.x_adjustment_account_id.display_name})")
             if quant.x_adjustment_account_id:
                 quant_account_map[quant.id] = quant.x_adjustment_account_id.id

        # Log para ver el mapa construido
        _logger.info(f"[Paso 1 & 2 - Check 1] Mapa de Cuentas Personalizadas Creado: {quant_account_map}")

        # Preparamos el contexto para pasarlo a super()
        final_ctx = self.env.context.copy() # Copiamos el contexto actual
        if quant_account_map:
            final_ctx['custom_adjustment_accounts'] = quant_account_map
            _logger.info(f"[Paso 1 & 2 - Check 2] Contexto modificado para pasar a super(): {final_ctx}")
            # Llamamos a super() usando el contexto modificado
            res = super(StockQuant, self.with_context(final_ctx))._apply_inventory()
        else:
             _logger.info("[Paso 1 & 2 - Check 2] No hay cuentas personalizadas, llamando a super() con contexto original.")
             # Llamamos a super() usando el contexto original
             res = super(StockQuant, self)._apply_inventory()

        # Log al final del método
        _logger.info(f"--- Fin _apply_inventory para Quants: {self.ids} ---")

        # Considera limpiar el campo DESPUÉS de llamar a super() y confirmar que fue exitoso
        # Podrías querer hacerlo solo si res es True o no hay errores, pero es complejo.
        # Ejemplo simple (sin garantía de éxito de la operación completa):
        # self.filtered(lambda q: q.x_adjustment_account_id).write({'x_adjustment_account_id': False})

        return res

    # --- Métodos Adicionales (UI/Cálculos) ---
    @api.onchange('inventory_quantity')
    def _onchange_inventory_quantity_clear_account(self):
        """ Limpia la cuenta personalizada si la diferencia es cero o no se ha contado."""
        if not self.inventory_quantity_set or float_is_zero(self.inventory_quantity - self.quantity, precision_rounding=self.product_uom_id.rounding):
             self.x_adjustment_account_id = False

    # Método importante para calcular la diferencia (verificar si Odoo 17 lo necesita explícito)
    # @api.depends('inventory_quantity', 'quantity', 'inventory_quantity_set') # Ajustar dependencias si es necesario
    # def _compute_inventory_diff_quantity(self): # Nombre más estándar en Odoo
    #     for quant in self:
    #         if quant.inventory_quantity_set:
    #             quant.inventory_diff_quantity = quant.inventory_quantity - quant.quantity
    #         else:
    #             quant.inventory_diff_quantity = 0
    # inventory_diff_quantity = fields.Float(compute='_compute_inventory_diff_quantity', ...) # Si defines el campo

    # Este método puede ser llamado al hacer clic en "Aplicar" en la vista de lista
    # OJO: Verifica si el botón estándar de Odoo 17 llama a este método o a _apply_inventory directamente.
    #      Si llama a _apply_inventory, este método podría no ser necesario o causar doble ejecución del contexto.
    #      Por seguridad, podrías comentar este método si no estás seguro que se use.
    def action_apply_inventory(self):
        _logger.info(f"--- Inicio action_apply_inventory para Quants: {self.ids} ---")
        quant_account_map = {
            quant.id: quant.x_adjustment_account_id.id
            for quant in self if quant.x_adjustment_account_id
        }
        _logger.info(f"Mapa de Cuentas (desde action_apply_inventory): {quant_account_map}")
        ctx = self.env.context.copy()
        if quant_account_map:
            ctx['custom_adjustment_accounts'] = quant_account_map
            _logger.info(f"Contexto a pasar desde action_apply_inventory: {ctx}")

        # Llamar a _apply_inventory CON el contexto (puede ser redundante si _apply_inventory ya lo hace)
        self.with_context(ctx)._apply_inventory()

        _logger.info(f"--- Fin action_apply_inventory para Quants: {self.ids} ---")
        # Es posible que necesites devolver una acción o True/False dependiendo de Odoo 17
        # Devolver True suele ser seguro para cerrar asistentes o indicar éxito simple.
        return {'type': 'ir.actions.act_window_close'} # Acción común para botones