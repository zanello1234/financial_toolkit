# Corrección del Ending Balance en Resúmenes de Tarjeta de Crédito

## Problema Identificado

El **Ending Balance** en los resúmenes de tarjeta de crédito no se calculaba correctamente. Estaba siendo calculado como la suma de las líneas del statement en lugar de representar la deuda total a pagar.

## Solución Implementada

### 1. **Nuevo Campo: Saldo Cuenta Contable**
```python
account_balance = fields.Monetary(
    string='Saldo Cuenta Contable',
    currency_field='currency_id',
    help="Credit card account balance at statement closing date"
)
```

### 2. **Corrección del Ending Balance**
- **Antes**: `balance_end_real = sum(statement.line_ids.mapped('amount'))`
- **Ahora**: `balance_end_real = statement_total_general` (deuda total a pagar)

### 3. **Campos Mostrados en Vistas**

#### En Tree View:
- **Ending Balance**: Deuda total a pagar
- **Saldo Cuenta**: Saldo real de la cuenta contable
- **Deuda ARS**: Deuda en pesos
- **Deuda USD**: Deuda en dólares

#### En Form View:
- **Información de Tarjeta de Crédito**:
  - Fecha de Cierre y Vencimiento
  - Saldo Cuenta Contable
  - Total Deuda Calculada
- **Desglose por Moneda**:
  - Deuda ARS/USD
  - Totales calculados ARS/USD
- **Alertas de Validación**

### 4. **Lógica de Actualización**
```python
def action_close_statement(self):
    # Capturar saldo real de la cuenta
    account_balance = self.journal_id._get_credit_card_balance()
    
    # Ending balance = deuda total a pagar
    ending_balance = self.total_to_pay
    
    statement.write({
        'balance_end_real': ending_balance,     # = Deuda total
        'account_balance': account_balance,     # = Saldo cuenta real
        'statement_total_general': self.total_to_pay,
        # ... otros campos
    })
```

## Interpretación de Campos

### **Ending Balance**
- **Concepto**: Deuda total que queda pendiente de pago
- **Fórmula**: `Saldo Anterior + Consumos + Gastos - Pagos`
- **Signo**: Negativo = Deuda, Positivo = Saldo a favor

### **Saldo Cuenta Contable** 
- **Concepto**: Saldo real de la cuenta contable al cierre
- **Origen**: `journal.default_account_id` balance
- **Uso**: Validación y reconciliación

### **Diferencias Posibles**
Si `Ending Balance ≠ Saldo Cuenta`, puede indicar:
- Movimientos no reconciliados
- Transacciones fuera del período del resumen
- Ajustes manuales en la cuenta

## Beneficios

✅ **Ending Balance correcto**: Representa la deuda real a pagar
✅ **Transparencia**: Se muestra tanto la deuda calculada como el saldo contable real
✅ **Validación**: Permite detectar discrepancias fácilmente
✅ **Trazabilidad**: Cada campo tiene su propósito específico
✅ **Reconciliación**: Mejor control de movimientos

## Ejemplo Práctico

```
Resumen Octubre 2025:
- Saldo Anterior: $-1,585.00 (deuda)
- Consumos: $2,000.00
- Gastos: $100.00
- Pagos: $500.00

Cálculo:
Total a Pagar = -1,585 + 2,000 + 100 - 500 = $15.00 (deuda)

Resultado:
- Ending Balance: $15.00 (deuda total a pagar)
- Saldo Cuenta: $15.00 (si coincide = OK)
```

Este enfoque proporciona claridad total sobre la situación financiera de la tarjeta de crédito y facilita la validación de saldos.