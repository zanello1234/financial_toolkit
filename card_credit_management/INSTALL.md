# Guía de Instalación y Configuración

## Requisitos Previos

### Módulos Dependientes
Asegúrese de que los siguientes módulos estén instalados:
- `account` (Contabilidad)
- `sale` (Ventas)
- `account_payment_pro` (Pagos Avanzados)
- `card_installment` (Cuotas de Tarjeta)
- `account_bank_statement_import` (Importación de Extractos)

### Versión de Odoo
- Compatible con Odoo 18.0 y versiones superiores

## Instalación

### 1. Copiar Módulo
```bash
# Copiar el módulo a la carpeta de addons
cp -r card_credit_management /path/to/odoo/addons/
```

### 2. Actualizar Lista de Aplicaciones
```bash
# Reiniciar servidor Odoo con actualización de módulos
./odoo-bin -u all -d your_database --stop-after-init
```

### 3. Instalar Módulo
1. Acceder a Odoo como administrador
2. Ir a Aplicaciones
3. Buscar "Credit Card Management"
4. Hacer clic en "Instalar"

## Configuración Inicial

### 1. Configurar Plan de Cuentas

#### Crear Cuentas Contables
Navegar a **Contabilidad > Configuración > Plan de Cuentas** y crear:

```
6201 - Gastos Bancarios - Tarjetas de Crédito
6202 - Costos Financieros - Tarjetas de Crédito  
1190 - Transferencia de Liquidez - Tarjetas
```

### 2. Configurar Diarios de Tarjetas

#### Crear Diarios Bancarios
Ir a **Contabilidad > Configuración > Diarios**

**Para Visa:**
- Nombre: "Visa"
- Código: "VISA"
- Tipo: "Banco"
- Marcar "Es Diario de Tarjeta de Crédito"
- Cuenta de Transferencia de Liquidez: "1190"
- Banco Final: Seleccionar banco destino

**Para Mastercard:**
- Nombre: "Mastercard"  
- Código: "MCARD"
- Tipo: "Banco"
- Marcar "Es Diario de Tarjeta de Crédito"
- Cuenta de Transferencia de Liquidez: "1190"
- Banco Final: Seleccionar banco destino

### 3. Configurar Planes de Tarjeta

Ir a **Tarjetas de Crédito > Configuración > Planes de Tarjeta**

#### Plan Débito Visa
- Nombre: "Débito"
- Diario: "Visa"
- Días de Acreditación: 2
- Porcentaje Arancel: 1.8%
- Porcentaje Costo Financiero: 0%
- Coeficiente Recargo: 1.0
- Factor Redondeo: 10
- Cuenta Arancel: "6201"
- Cuenta Costo Financiero: "6202"

#### Plan Cuota Simple Tres Visa
- Nombre: "Cuota Simple Tres"
- Diario: "Visa"
- Días de Acreditación: 10
- Porcentaje Arancel: 1.8%
- Porcentaje Costo Financiero: 5.87%
- Coeficiente Recargo: 1.0587
- Factor Redondeo: 10
- Cuenta Arancel: "6201"
- Cuenta Costo Financiero: "6202"

### 4. Configurar Feriados

Ir a **Tarjetas de Crédito > Configuración > Feriados**

Agregar los feriados nacionales para el año en curso:
- 1 de Enero - Año Nuevo
- Lunes y Martes de Carnaval
- 2 de Abril - Malvinas
- Viernes Santo
- 1 de Mayo - Día del Trabajador
- 25 de Mayo - Revolución de Mayo
- 20 de Junio - Belgrano
- 9 de Julio - Independencia
- 17 de Agosto - San Martín
- 12 de Octubre - Diversidad Cultural
- 20 de Noviembre - Soberanía Nacional
- 8 de Diciembre - Inmaculada Concepción
- 25 de Diciembre - Navidad

### 5. Configurar Modelos de Conciliación

Para cada diario de tarjeta, crear modelos de conciliación:

#### Gastos Bancarios
- Nombre: "Gastos Bancarios - Visa"
- Tipo: "Sugerencia de Diferencia"
- Texto de Coincidencia: "ARANCEL"
- Cuenta: "6201 - Gastos Bancarios"

#### IVA Crédito
- Nombre: "IVA Crédito - Visa"
- Tipo: "Sugerencia de Diferencia"
- Texto de Coincidencia: "IVA"
- Cuenta: IVA Compras (según configuración)

#### Ingresos Brutos
- Nombre: "Ingresos Brutos - Visa"
- Tipo: "Sugerencia de Diferencia"
- Texto de Coincidencia: "SIRTAC"
- Cuenta: Configurar según jurisdicción

## Configuración de Usuarios

### Permisos de Seguridad

#### Gestor de Tarjetas de Crédito
- Acceso completo a configuración y operaciones
- Puede crear/modificar planes y feriados
- Acceso a todas las vistas y reportes

#### Usuario de Tarjetas de Crédito
- Acceso de lectura a configuración
- Puede crear y modificar acreditaciones
- Acceso a operaciones diarias

### Asignar Permisos
1. Ir a **Configuración > Usuarios y Compañías > Usuarios**
2. Seleccionar usuario
3. En "Otros", agregar grupo correspondiente:
   - "Credit Card Manager" para gestores
   - "Credit Card User" para usuarios

## Flujo de Trabajo Recomendado

### 1. Configuración Inicial (Una vez)
1. Configurar cuentas contables
2. Crear diarios de tarjetas
3. Configurar planes de tarjeta
4. Cargar feriados anuales
5. Crear modelos de conciliación

### 2. Proceso de Venta
1. En cotización, seleccionar plan de tarjeta
2. Hacer clic en "Calcular Recargo"
3. Confirmar orden de venta
4. Generar factura

### 3. Proceso de Cobranza
1. Registrar pago con diario de tarjeta
2. Completar plan, lote y cupón
3. Sistema crea acreditación automáticamente

### 4. Conciliación Mensual
1. Importar extracto de tarjeta
2. Usar vista de conciliación rápida
3. Buscar por números de lote
4. Aplicar modelos de conciliación
5. Crear transferencia de liquidez

### 5. Seguimiento
1. Monitorear acreditaciones pendientes
2. Verificar fechas estimadas vs reales
3. Generar reportes de gestión

## Solución de Problemas

### Error: "Plan de tarjeta requerido"
- Verificar que el diario esté marcado como tarjeta de crédito
- Configurar al menos un plan para el diario

### Error: "Recalcular recargo"
- El total de la orden cambió después del cálculo
- Hacer clic nuevamente en "Calcular Recargo"

### No aparecen días hábiles correctos
- Verificar configuración de feriados
- Asegurar que las fechas estén en el formato correcto

### Saldo del diario no queda en cero
- Verificar que todos los movimientos estén conciliados
- Revisar que la transferencia de liquidez sea por el monto correcto

## Mantenimiento

### Tareas Periódicas
- Actualizar feriados para el nuevo año
- Revisar y ajustar planes de tarjeta según nuevas condiciones
- Archivar acreditaciones antiguas (más de 2 años)
- Verificar modelos de conciliación

### Backup de Configuración
- Exportar configuración de planes de tarjeta
- Respaldar modelos de conciliación
- Documentar configuración de cuentas contables

## Soporte

Para soporte técnico o personalizaciones:
- Email: support@adhoc.com.ar
- Web: www.adhoc.com.ar
- Documentación: Ver README.md y TECHNICAL_DOCS.md