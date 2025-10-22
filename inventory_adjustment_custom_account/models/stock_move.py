# -*- coding: utf-8 -*-
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class StockMove(models.Model):
    _inherit = 'stock.move'

    # =========================================================================
    # HERENCIA DE _account_entry_move (VERSIÓN CON CORRECCIÓN FINAL)
    # Lee el contexto directamente e intenta modificar los valores del asiento
    # ANTES de que se cree, usando 'balance' para identificar la línea correcta.
    # =========================================================================
    def _account_entry_move(self, qty, description, svl_id, cost):
        _logger.info(f"--- Inicio _account_entry_move para Move: {self.id}, svl_id: {svl_id} ---")
        _logger.info(f"Valor de qty recibido: {qty}") # Log para ver signo cantidad

        # Llamar a super() para obtener los valores estándar del asiento
        am_vals_list = super()._account_entry_move(qty, description, svl_id, cost)

        # Log para ver la estructura completa de lo que devuelve super()
        _logger.info(f"Valores COMPLETOS de super() en _account_entry_move para Move {self.id}: {am_vals_list}")

        # Si no hay valores de asiento estándar o falta svl_id, retornamos original
        if not am_vals_list or not svl_id:
            _logger.info(f"Move {self.id}: No hay valores de asiento o falta svl_id. Retornando valores originales.")
            return am_vals_list

        # Intentar leer el mapa de cuentas directamente del contexto
        quant_account_map = self.env.context.get('custom_adjustment_accounts', {})
        _logger.info(f"Move {self.id}: Leyendo contexto 'custom_adjustment_accounts': {quant_account_map}")

        # Si el mapa está vacío, no hay nada que hacer
        if not quant_account_map:
            _logger.info(f"Move {self.id}: Mapa de cuentas personalizado vacío en contexto. No se modifica asiento.")
            return am_vals_list

        # --- Lógica (frágil) para encontrar el quant ID original ---
        relevant_quant_id = False # Inicializar a False
        active_id_from_context = self.env.context.get('active_id')
        try:
            if len(quant_account_map) == 1 and active_id_from_context and active_id_from_context in quant_account_map:
                 relevant_quant_id = active_id_from_context
                 _logger.debug(f"Usando active_id {active_id_from_context} del contexto para Move {self.id}")
            elif len(quant_account_map) == 1:
                 relevant_quant_id = list(quant_account_map.keys())[0]
                 _logger.debug(f"Asumiendo quant {relevant_quant_id} (único en mapa) para Move {self.id}")
        except Exception as e:
            _logger.error(f"Error al intentar identificar relevant_quant_id para Move {self.id}: {e}")
        # --- Fin lógica frágil ---

        # Log de verificación del Quant ID relevante
        _logger.info(f"Move {self.id}: Quant ID relevante (intentado): {relevant_quant_id}")

        # Obtener la cuenta personalizada del mapa usando el quant ID encontrado
        custom_account_id = quant_account_map.get(relevant_quant_id) if relevant_quant_id else None
        _logger.info(f"Move {self.id}: Cuenta personalizada obtenida del mapa para quant {relevant_quant_id}: {custom_account_id}")

        # Si SÍ encontramos una cuenta personalizada aplicable
        if custom_account_id:
            # Asumimos que super() devuelve lista con un dict; trabajamos sobre él
            am_vals = am_vals_list[0]
            lines_vals = am_vals.get('line_ids', []) # Obtenemos la lista de tuplas de líneas

            # Calcular la cuenta default (misma lógica que antes)
            default_account_id = False
            move = self.env['stock.move'].browse(self.id) # Necesitamos el registro del move actual
            if move:
                if qty < 0: # Menos stock
                    if move.location_dest_id.usage == 'inventory':
                        default_account_id = move.location_dest_id.valuation_in_account_id.id # Cuenta Entrada de Ubic. Ajuste
                else: # Más stock (qty >= 0)
                    if move.location_id.usage == 'inventory':
                        default_account_id = move.location_id.valuation_out_account_id.id # Cuenta Salida de Ubic. Ajuste
                _logger.info(f"Move {self.id}: Calculada default_account_id = {default_account_id}")
            else:
                 _logger.warning(f"Move {self.id}: No se pudo obtener registro de stock.move para calcular default_account_id.")

            # Proceder solo si tenemos cuenta default y es diferente de la personalizada
            if default_account_id and default_account_id != custom_account_id:
                modified = False
                # Iterar sobre las líneas preparadas en am_vals['line_ids']
                for line_tuple in lines_vals:
                    # Formato esperado: (0, 0, {diccionario_valores_linea})
                    if len(line_tuple) == 3 and isinstance(line_tuple[2], dict):
                        line_vals = line_tuple[2] # El diccionario con los datos de la línea
                        # Verificar si la cuenta es la default que buscamos
                        if line_vals.get('account_id') == default_account_id:
                            is_counterpart = False
                            # --- LÓGICA CORREGIDA USANDO BALANCE ---
                            balance = line_vals.get('balance', 0)
                            if qty < 0 and balance > 0: # Disminución -> Contrapartida es Débito (balance > 0)
                                is_counterpart = True
                            elif qty >= 0 and balance < 0: # Aumento -> Contrapartida es Crédito (balance < 0)
                                is_counterpart = True
                            # --- FIN LÓGICA CORREGIDA ---

                            _logger.info(f"Move {self.id}: Revisando línea con cuenta {default_account_id}. ¿Es contrapartida? {is_counterpart}. Contenido línea: {line_vals}")

                            if is_counterpart:
                                _logger.info(f"Move {self.id}: ¡¡MODIFICANDO VALORES LÍNEA!! (cuenta {default_account_id} -> {custom_account_id}). Línea original: {line_vals}")
                                # Modificamos directamente el diccionario de valores DENTRO de la tupla/lista
                                line_vals['account_id'] = custom_account_id
                                current_name = line_vals.get('name', '')
                                # Intentar obtener el código de la cuenta (mejor si está disponible)
                                account_code = self.env['account.account'].browse(custom_account_id).code
                                line_vals['name'] = f"{current_name} (Cuenta Ajuste: {account_code or 'N/A'})"
                                modified = True
                                break # Asumimos que solo hay una línea de contrapartida a modificar
                if not modified:
                     _logger.warning(f"Move {self.id}: Se obtuvo cuenta {custom_account_id} del contexto pero no se encontró/modificó la línea con cuenta default {default_account_id} en los valores.")

            elif default_account_id == custom_account_id:
                 _logger.info(f"Move {self.id}: Cuenta personalizada {custom_account_id} es igual a la default {default_account_id}. No se modifica.")
            else:
                 # Esto cubre el caso donde default_account_id fue False o no aplicaba
                 _logger.info(f"Move {self.id}: No se calculó cuenta default válida o ubicación no era 'inventory'. No se intenta modificar.")
        else:
             _logger.info(f"Move {self.id}: No se encontró cuenta personalizada aplicable en el mapa/contexto. No se modifica.")

        _logger.info(f"--- Fin _account_entry_move para Move: {self.id}, svl_id: {svl_id} ---")
        # Devolvemos la lista de diccionarios (potencialmente modificada)
        return am_vals_list