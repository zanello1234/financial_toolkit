# Sistema de KPIs Universal - Account Dashboard Banner

## Descripción General

Se ha extendido completamente el sistema de KPIs para permitir la creación de indicadores personalizados usando **cualquier cuenta** en **cualquier tipo de KPI**. Ahora puedes usar la configuración de cuentas personalizada en todos los tipos de celda disponibles.

## Nueva Funcionalidad Universal

### **Configuración de Cuentas Disponible en Todos los Tipos de KPI**

Ahora **TODOS** los tipos de KPI pueden usar configuración personalizada de cuentas:
- `liquidity`: KPIs de liquidez
- `account_balance`: KPIs de saldo de cuentas  
- `count`: Conteo con filtros de cuenta
- `sum`: Suma con filtros de cuenta
- `customer_debt`, `supplier_debt`: Deudas con cuentas específicas
- `income`: Ingresos de cuentas personalizadas
- Y **cualquier otro tipo de KPI existente**

### **Modos de Selección Universal**

Todos los KPIs ahora soportan tres modos de selección:

#### Modo "Por Tipo de Cuenta" (`by_type`)
- Selecciona automáticamente todas las cuentas de un tipo específico
- Tipos disponibles:
  - `asset_receivable`: Cuentas por cobrar
  - `asset_cash`: Efectivo y equivalentes
  - `asset_current`: Activos corrientes
  - `asset_non_current`: Activos no corrientes
  - `asset_prepayments`: Gastos pagados por adelantado
  - `asset_fixed`: Activos fijos
  - `liability_payable`: Cuentas por pagar
  - `liability_credit_card`: Tarjetas de crédito
  - `liability_current`: Pasivos corrientes
  - `liability_non_current`: Pasivos no corrientes
  - `equity`: Patrimonio
  - `equity_unaffected`: Utilidades no distribuidas
  - `income`: Ingresos
  - `income_other`: Otros ingresos
  - `expense`: Gastos
  - `expense_depreciation`: Depreciación
  - `expense_direct_cost`: Costos directos
  - `off_balance`: Cuentas de orden

#### Modo "Cuentas Específicas" (`specific`)
- Permite seleccionar cuentas individuales manualmente
- Útil para KPIs muy específicos o combinaciones particulares

### 3. Compatibilidad Retroactiva

El sistema mantiene total compatibilidad con los KPIs de liquidez existentes:
- Los KPIs de liquidez siguen funcionando exactamente igual
- Se mantienen todos los campos y funcionalidades originales
- No se requiere migración de datos existentes

## Uso Ejemplo

### Crear KPI de Gastos con Cualquier Tipo de Celda

1. **Tipo de Celda**: Seleccionar **cualquier tipo** (ej: "Liquidity", "Count", "Sum", etc.)
2. **Modo de Selección**: "Por Tipo de Cuenta"  
3. **Tipo de Cuenta**: "Gastos" (expense)
4. **Resultado**: Mostrará el total de todas las cuentas de gastos

### Crear KPI de Ingresos Específicos con Tipo "Customer Debt"

1. **Tipo de Celda**: Seleccionar "Customer Debt"
2. **Modo de Selección**: "Cuentas Específicas"
3. **Cuentas**: Seleccionar cuentas de ingresos específicas
4. **Resultado**: Mostrará el saldo de esas cuentas en lugar del cálculo original

### Usar Cualquier KPI con Cuentas Personalizadas

**TODOS** los tipos de KPI ahora respetan la configuración de cuentas personalizada cuando está configurada, ofreciendo flexibilidad total.

## Características Técnicas

### Manejo Automático de Signos
El sistema ajusta automáticamente el signo del saldo según el tipo de cuenta:
- **Activos**: Débito positivo (saldo normal al débito)
- **Pasivos**: Crédito positivo (saldo normal al crédito)
- **Patrimonio**: Crédito positivo (saldo normal al crédito)
- **Ingresos**: Crédito positivo (saldo normal al crédito)
- **Gastos**: Débito positivo (saldo normal al débito)

### Performance Optimizada
- Consultas SQL optimizadas para manejar múltiples cuentas
- Cache de resultados para mejorar la velocidad
- Filtrado eficiente por tipo de cuenta

## Archivos Modificados

### Modelo Principal
- `models/account_dashboard_banner_cell.py`:
  - Agregado campo `account_type_filter`
  - Agregado campo `account_selection_mode`
  - Agregado método `_prepare_cell_data_account_balance()`
  - Extendido método `_prepare_cell_data_liquidity()` para mayor flexibilidad

### Vista de Formulario
- `views/account_dashboard_banner_cell.xml`:
  - Agregada sección de configuración de cuentas genéricas
  - Mejorada la interfaz de usuario con explicaciones claras
  - Mantenida compatibilidad con configuración de liquidez existente

## Ventajas del Sistema Universal

1. **Flexibilidad Máxima**: Cualquier KPI puede usar cualquier cuenta
2. **Simplicidad**: Un solo sistema de configuración para todos los tipos
3. **Compatibilidad**: No rompe funcionalidad existente (modo legacy disponible)
4. **Intuitividad**: Interfaz unificada y clara
5. **Performance**: Optimizado para consultas eficientes
6. **Extensibilidad**: Fácil agregar nuevos tipos de cuenta
7. **Consistencia**: Comportamiento uniforme en todos los KPIs

## Próximos Pasos Sugeridos

1. **Pruebas**: Crear varios KPIs de prueba para validar funcionamiento
2. **Documentación**: Crear ejemplos específicos para usuarios finales
3. **Capacitación**: Entrenar usuarios en las nuevas funcionalidades
4. **Monitoreo**: Verificar performance con datos reales