# Validación del Flujo de Tarjeta de Crédito

## Flujo Completo Esperado

### 1. **Estado Inicial**
- Se configuran pagos a proveedores usando la tarjeta de crédito
- Estos pagos quedan en estado `in_process`
- Los pagos tienen `journal_id` = tarjeta de crédito
- Los pagos tienen `partner_id.supplier_rank > 0`

### 2. **Botón "Resumen" - Importación**
- Se abre el wizard `credit.card.statement.wizard`
- Estado inicial: `import`
- Se calcula automáticamente:
  - **Saldo anterior**: Del último resumen cerrado
  - **Consumos**: Pagos `in_process` a proveedores desde la tarjeta
  - **Pagos a tarjeta**: Pagos `in_process` hacia la tarjeta
- Se ejecuta `action_generate_statement()`:
  - Crea un `account.bank.statement`
  - Importa solo pagos y consumos (NO gastos aún)
  - Cambia estado a `charges`

### 3. **Estado "Charges" - Agregar Gastos**
- Usuario puede ingresar:
  - Impuestos, Intereses, Sellados, Otros gastos
- Se ejecuta `action_add_charges()`:
  - Agrega líneas de gastos al statement existente
  - Cambia estado a `close`

### 4. **Estado "Close" - Cerrar Resumen**
- Se muestran totales finales por moneda
- Se ejecuta `action_close_statement()`:
  - Guarda totales en el statement
  - Reconcilia automáticamente las líneas
  - Cierra el statement

### 5. **Botón "Pagar" - Nuevo Ciclo**
- Se abre `credit.card.payment.wizard`
- Lee saldos del último statement cerrado
- Permite pagos parciales o totales
- Crea pagos `in_process` hacia la tarjeta
- Estos pagos aparecerán en el próximo resumen

## Convenciones de Signos

### En Statement Lines:
- **Consumos**: Negativos (aumentan deuda)
- **Pagos a tarjeta**: Positivos (reducen deuda)  
- **Gastos**: Negativos (aumentan deuda)

### En Wizard (Para UI):
- **Todos los montos se muestran como positivos**
- **Los cálculos internos manejan signos correctamente**

## Validaciones Críticas

### ✅ **Punto 1**: Filtro de Pagos a Proveedores
```python
consumption_payments = self.env['account.payment'].search([
    ('journal_id', '=', record.journal_id.id),
    ('state', '=', 'in_process'),  
    ('payment_type', '=', 'outbound'),
    ('partner_id.supplier_rank', '>', 0),  # CLAVE: Solo proveedores
])
```

### ✅ **Punto 2**: Filtro de Pagos a Tarjeta
```python
credit_card_payments = self.env['account.payment'].search([
    ('destination_journal_id', '=', record.journal_id.id),
    ('state', '=', 'in_process'),
    ('payment_type', '=', 'outbound'),
])
```

### ✅ **Punto 3**: Prevención de Duplicados
```python
# Filtrar por payment_ref ya utilizado
used_payment_names = set(existing_statement_lines.mapped('payment_ref'))
available_payments = payments.filtered(lambda p: p.name not in used_payment_names)
```

### ✅ **Punto 4**: Separación de Fases
- `action_generate_statement()`: Solo pagos y consumos
- `action_add_charges()`: Solo gastos del resumen
- NO duplicación de gastos

### ✅ **Punto 5**: Reconciliación Automática
```python
def _auto_reconcile_statement_lines(self, statement):
    # Vincula statement lines con payment moves
    # Reconcilia move lines del mismo account
```

## Escenario de Prueba

### Datos de Entrada:
1. **Journal Tarjeta**: `journal_credit_card` (type='bank', is_credit_card=True)
2. **Journal Banco**: `journal_bank` (type='bank')
3. **Proveedor**: `supplier_xyz`
4. **Monedas**: ARS, USD

### Transacciones:
1. **Pago a Proveedor**: $10,000 ARS desde tarjeta (in_process)
2. **Pago a Proveedor**: $500 USD desde tarjeta (in_process)  
3. **Pago a Tarjeta**: $5,000 ARS desde banco (in_process)

### Flujo:
1. **Resumen → Import**: Detecta 3 pagos, crea statement
2. **Charges**: Agrega $100 ARS impuestos
3. **Close**: 
   - Saldo ARS: $10,000 + $100 - $5,000 = $5,100 (deuda)
   - Saldo USD: $500 (deuda)
4. **Pagar**: Pago de $3,000 ARS queda para próximo resumen

### Resultado Esperado:
- Statement cerrado con saldo correcto
- Líneas reconciliadas automáticamente
- Próximo resumen iniciará con saldo anterior correcto