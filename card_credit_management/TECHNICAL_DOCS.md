# Documentación Técnica - Módulo de Gestión de Tarjetas de Crédito

## Arquitectura del Módulo

### Modelos Principales

#### 1. `card.plan` - Planes de Tarjeta de Crédito
Gestiona la configuración de planes de tarjeta con sus respectivos costos y términos.

**Campos principales:**
- `name`: Nombre del plan (ej: "Cuota Simple Tres", "Débito")
- `journal_id`: Diario asociado (Visa, Mastercard, etc.)
- `accreditation_days`: Días hábiles para acreditación
- `fee_percentage`: Porcentaje de arancel
- `financial_cost_percentage`: Porcentaje de costo financiero
- `surcharge_coefficient`: Coeficiente para cálculo de recargo
- `rounding_factor`: Factor de redondeo (10, 100, 1000)

**Métodos principales:**
- `calculate_estimated_amount(original_amount)`: Calcula monto estimado a liquidar
- `calculate_surcharge(base_amount)`: Calcula recargo con redondeo
- `calculate_accreditation_date(collection_date)`: Calcula fecha de acreditación

#### 2. `card.holiday` - Feriados
Gestiona los feriados para cálculo preciso de días hábiles.

**Campos principales:**
- `name`: Nombre del feriado
- `date`: Fecha del feriado
- `recurring`: Si se repite anualmente
- `notes`: Notas adicionales

#### 3. `card.accreditation` - Seguimiento de Acreditaciones
Rastrea las acreditaciones de tarjetas de crédito desde el cobro hasta la conciliación.

**Campos principales:**
- `payment_id`: Pago relacionado
- `partner_id`: Cliente
- `journal_id`: Diario de tarjeta
- `card_plan_id`: Plan de tarjeta utilizado
- `batch_number`: Número de lote
- `coupon_number`: Número de cupón
- `collection_date`: Fecha de cobro
- `original_amount`: Monto original
- `estimated_accreditation_date`: Fecha estimada de acreditación
- `estimated_liquidation_amount`: Monto estimado a liquidar
- `state`: Estado (pending, credited, reconciled)

### Extensiones de Modelos Existentes

#### `sale.order` - Órdenes de Venta
**Campos agregados:**
- `card_plan_id`: Plan de tarjeta seleccionado
- `card_surcharge_amount`: Monto del recargo calculado
- `card_surcharge_calculated`: Flag de recargo calculado
- `card_base_amount`: Monto base para cálculo de recargo

**Métodos principales:**
- `action_calculate_card_surcharge()`: Calcula y aplica recargo
- `_create_surcharge_line()`: Crea línea de recargo en la orden

#### `account.payment` - Pagos
**Campos agregados:**
- `card_plan_id`: Plan de tarjeta del pago
- `card_batch_number`: Número de lote
- `card_coupon_number`: Número de cupón
- `estimated_accreditation_date`: Fecha estimada de acreditación
- `estimated_liquidation_amount`: Monto estimado a liquidar

#### `account.journal` - Diarios
**Campos agregados:**
- `is_credit_card`: Flag de diario de tarjeta de crédito
- `card_plan_ids`: Planes asociados al diario
- `transfer_liquidity_account_id`: Cuenta puente para transferencias
- `final_bank_journal_id`: Diario bancario final

## Flujo de Trabajo Técnico

### 1. Proceso de Venta con Recargo

```python
# 1. Usuario selecciona plan de tarjeta en la orden de venta
sale_order.card_plan_id = plan_id

# 2. Sistema calcula recargo
base_amount = sale_order.amount_total - sale_order.card_surcharge_amount
surcharge = plan.calculate_surcharge(base_amount)

# 3. Crea línea de recargo
sale_order._create_surcharge_line(surcharge)

# 4. Valida consistencia antes de confirmar
if abs(current_base - recorded_base) > 0.01:
    raise ValidationError("Recalculate surcharge")
```

### 2. Registro de Pago y Acreditación

```python
# 1. Al confirmar pago con diario de tarjeta
if payment.journal_id.is_credit_card:
    # 2. Validar campos obligatorios
    if not payment.card_plan_id:
        raise ValidationError("Plan required")
    
    # 3. Crear registro de acreditación
    accreditation = env['card.accreditation'].create({
        'payment_id': payment.id,
        'batch_number': payment.card_batch_number,
        'estimated_accreditation_date': plan.calculate_accreditation_date(payment.date),
        'estimated_liquidation_amount': plan.calculate_estimated_amount(payment.amount)
    })
```

### 3. Cálculo de Días Hábiles

```python
def calculate_accreditation_date(self, collection_date):
    holidays = self.env['card.holiday'].search([])
    holiday_dates = [h.date for h in holidays]
    
    current_date = collection_date
    business_days_count = 0
    
    while business_days_count < self.accreditation_days:
        current_date = fields.Date.add(current_date, days=1)
        weekday = current_date.weekday()
        
        # Lunes=0, Domingo=6
        if weekday < 5 and current_date not in holiday_dates:
            business_days_count += 1
    
    return current_date
```

### 4. Conciliación Bancaria

```python
# 1. Importar extracto de tarjeta
statement_lines = import_credit_card_statement()

# 2. Buscar acreditaciones por lote
batch_number = extract_batch_from_reference(line.payment_ref)
accreditations = env['card.accreditation'].search([
    ('batch_number', '=', batch_number),
    ('state', '!=', 'reconciled')
])

# 3. Aplicar modelos de conciliación predeterminados
reconcile_model.apply_to_statement_line(line)

# 4. Transferir liquidez neta
transfer_wizard.action_create_transfer()
```

## Configuración de Cuentas Contables

### Cuentas Principales
- **6201**: Gastos Bancarios (Aranceles)
- **6202**: Costos Financieros (Intereses)
- **1190**: Transferencia de Liquidez (Cuenta Puente)
- **IVA Crédito**: Según configuración de la empresa
- **Ingresos Brutos**: Cuenta configurable por jurisdicción

### Asientos Contables Típicos

#### Registro de Venta con Recargo
```
Débito: Cliente                     $1000
Crédito: Ventas                     $940
Crédito: Intereses Ganados          $60
```

#### Registro de Pago
```
Débito: Visa (Banco)                $1000
Crédito: Cliente                    $1000
```

#### Conciliación de Extracto
```
Débito: Gastos Bancarios            $18
Débito: IVA Crédito                 $3.78
Crédito: Visa (Banco)               $21.78
```

#### Transferencia de Liquidez
```
# En diario de tarjeta:
Débito: Transferencia Liquidez      $978.22
Crédito: Visa (Banco)               $978.22

# En diario bancario final:
Débito: Banco Galicia               $978.22
Crédito: Transferencia Liquidez     $978.22
```

## Validaciones y Controles

### Validaciones de Datos
- Plan de tarjeta obligatorio para diarios de tarjeta
- Número de lote y cupón obligatorios en pagos
- Consistencia de recargo en órdenes de venta
- Fechas de feriados únicas

### Controles de Flujo
- Prevenir modificación de recargo después del cálculo
- Validar saldo cero en diario de tarjeta post-conciliación
- Verificar días hábiles en cálculo de acreditación

## Extensibilidad

### Puntos de Extensión
- Métodos de cálculo de recargo personalizables
- Modelos de conciliación configurables
- Integración con otros módulos de pago
- Reportes adicionales de gestión

### Hooks para Personalización
- `_calculate_custom_surcharge()`: Lógica de recargo personalizada
- `_get_reconcile_models()`: Modelos de conciliación específicos
- `_validate_card_payment()`: Validaciones adicionales de pago

## Consideraciones de Performance

### Optimizaciones Implementadas
- Índices en campos de búsqueda frecuente (batch_number, coupon_number)
- Cálculos almacenados para montos estimados
- Búsquedas eficientes por fecha y estado

### Recomendaciones
- Archivar acreditaciones antiguas periódicamente
- Limitar búsquedas por rango de fechas
- Usar filtros por estado en vistas principales