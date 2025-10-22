# Credit Card Journal Manager

## Descripción

Este módulo extiende la funcionalidad de los diarios de Odoo para proporcionar características específicas para tarjetas de crédito.

## Características

### Vista Kanban Mejorada
- **Botón "Pagar Tarjeta"**: Permite realizar pagos rápidos del saldo de la tarjeta de crédito
- **Botón "Emitir Resumen"**: Genera y muestra el resumen de transacciones de la tarjeta

### Funcionalidades

#### Pagar Tarjeta de Crédito
- Calcula automáticamente el saldo pendiente de la tarjeta
- Abre un asistente de pago preconfigurado
- Selecciona automáticamente el diario de pago apropiado
- Valida que solo se pueda usar en diarios de tarjeta de crédito

#### Emitir Resumen
- Muestra todas las transacciones del mes actual
- Filtra automáticamente por el diario de la tarjeta de crédito
- Vista optimizada para revisión de movimientos

### Detección Automática
El módulo detecta automáticamente si un diario es de tarjeta de crédito basándose en:
- Tipo de diario: "Bank"
- Nombre del diario contiene las palabras "credit" y "card"

## Instalación

1. Copiar el módulo a la carpeta de addons
2. Actualizar la lista de módulos
3. Instalar "Credit Card Journal Manager"

## Uso

### Configuración
1. Crear o configurar diarios de tipo "Bank"
2. Incluir "Credit Card" en el nombre del diario
3. Los botones aparecerán automáticamente en la vista kanban

### Operaciones
- **Dashboard de Contabilidad → Journals**: Ver todos los diarios
- **Dashboard de Contabilidad → Journals → Credit Cards**: Ver solo tarjetas de crédito
- **Hacer clic en "Pay Card"**: Iniciar proceso de pago
- **Hacer clic en "Statement"**: Ver resumen de transacciones

## Requisitos

- Odoo 18.0
- Módulo account (instalado por defecto)

## Configuración Recomendada

Para mejores resultados:
1. Configurar la cuenta contable por defecto del diario
2. Configurar la cuenta de suspense apropiada
3. Tener al menos un diario de banco o efectivo para pagos

## Personalización

El módulo puede personalizarse modificando:
- `_compute_is_credit_card()`: Lógica de detección de tarjetas de crédito
- `_get_payment_journal_id()`: Selección del diario de pago
- Vistas XML: Apariencia y posicionamiento de botones

## Licencia

AGPL-3.0 or later