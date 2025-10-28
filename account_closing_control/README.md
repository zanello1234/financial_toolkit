# Account Closing Control - Control de Cierre Contable

## 📋 Resumen del Módulo

**Account Closing Control** es un módulo completo para Odoo 18.0 que sistematiza, audita y controla el proceso de cierre contable mensual y anual. Proporciona un flujo de trabajo estructurado mediante checklists personalizables, validaciones automáticas y bloqueo seguro de períodos contables.

## 🎯 Objetivos Principales

- **Sistematizar** el proceso de cierre contable mediante plantillas reutilizables
- **Auditar** cada paso del cierre con trazabilidad completa
- **Controlar** el cumplimiento de tareas obligatorias antes del bloqueo
- **Automatizar** validaciones mediante código Python personalizable
- **Documentar** el proceso con reportes profesionales de auditoría

## 🏗️ Arquitectura del Módulo

### Modelos de Datos

#### 1. `closing.template` - Plantillas de Cierre
Define checklists reutilizables para diferentes tipos de cierre:
- **Campos principales**: `name`, `periodicity`, `company_id`, `line_ids`
- **Periodicidades**: Mensual, Trimestral, Anual
- **Reutilización**: Una plantilla puede generar múltiples hojas de cierre

#### 2. `closing.template.line` - Líneas de Plantilla
Define cada tarea del checklist:
- **Tipos de validación**:
  - **Manual**: El analista marca como completado
  - **Acción**: Abre vistas específicas de Odoo
  - **Python**: Ejecuta validaciones automáticas personalizables
- **Configuración**: `sequence`, `description`, `validation_type`, `python_code`, `required`

#### 3. `closing.worksheet` - Hojas de Cierre
Instancias de trabajo para períodos específicos:
- **Estados**: `draft` → `in_progress` → `to_review` → `done` → `cancel`
- **Seguimiento**: Progress tracking, task statistics, approval workflow
- **Bloqueo automático**: Establece fechas de bloqueo contable y fiscal

#### 4. `closing.worksheet.line` - Tareas de Cierre
Ejecución de tareas individuales:
- **Estados**: `pending`, `in_progress`, `done`, `failed`, `skipped`
- **Trazabilidad**: `user_id`, `completed_date`, `validation_log`, `notes`
- **Adjuntos**: Soporte para papeles de trabajo

### Wizard de Generación

#### `closing.wizard` - Asistente de Creación
- **Selección rápida**: Períodos mensuales, trimestrales, anuales
- **Fechas manuales**: Para períodos personalizados
- **Validaciones**: Previene cierres superpuestos
- **Generación automática**: Copia tareas desde plantilla

## 🔧 Funcionalidades Principales

### 1. Gestión de Plantillas
- Crear plantillas reutilizables para diferentes tipos de cierre
- Configurar tareas con validaciones manuales, de acción o Python
- Definir responsabilidades por grupo de usuarios
- Establecer secuencias y obligatoriedad de tareas

### 2. Ejecución de Cierres
- Generar hojas de cierre desde plantillas configuradas
- Ejecutar tareas según su tipo de validación
- Seguimiento en tiempo real del progreso
- Sistema de estados con flujo controlado

### 3. Validaciones Automáticas
Ejemplos de validaciones Python incluidas:
```python
# Validar cuentas puente en cero
bridge_accounts = env['account.account'].search([('code', 'like', '1199%')])
for account in bridge_accounts:
    if abs(account.balance) > 0.01:
        raise UserError(f"Cuenta {account.code} con saldo: {account.balance}")
```

### 4. Bloqueo de Períodos
- Bloqueo automático al aprobar cierre
- Establece `fiscalyear_lock_date` y `tax_lock_date`
- Previene creación de asientos en período cerrado
- Sistema de reapertura con trazabilidad

### 5. Reportes de Auditoría
- Reporte PDF profesional con:
  - Información general del cierre
  - Estadísticas de progreso
  - Detalle completo de tareas
  - Logs de validaciones
  - Información de bloqueo
  - Firmas y certificación

## 🔐 Sistema de Permisos

### Grupos de Usuarios

| Grupo | Plantillas | Hojas de Cierre | Capacidades Especiales |
|-------|------------|-----------------|------------------------|
| **Analista Contable** | Solo lectura | Crear, editar, enviar a revisión | Ejecutar tareas, no puede aprobar |
| **Gerente Contable** | Crear, editar | Control total | Aprobar cierres, bloquear períodos, reabrir |
| **Asesor Contable** | Control total | Control total | Borrar plantillas obsoletas |

### Flujo de Aprobación
1. **Analista** crea y ejecuta tareas → `in_progress`
2. **Analista** envía a revisión → `to_review`
3. **Gerente** aprueba y bloquea → `done`
4. **Gerente** puede reabrir si necesario → `in_progress`

## 🎨 Interfaz de Usuario

### Vistas Principales

#### 1. Vista Kanban - Hojas de Cierre
- Organizada por estados (Borrador, En Progreso, A Revisar, Cerrado)
- Tarjetas con progreso visual y acciones rápidas
- Indicadores de aprobación y fechas clave

#### 2. Vista Form - Hoja de Cierre
- **Header**: Botones de acción según estado actual
- **Información general**: Período, plantilla, estadísticas
- **Pestaña Tareas**: Grid editable con botones de acción
- **Pestaña Resumen**: Notas de cierre
- **Chatter**: Seguimiento de cambios y comentarios

#### 3. Vista Tree - Tareas de Cierre
- Indicadores visuales por estado de tarea
- Botones de acción contextual (Completar, Validar, Omitir)
- Información de responsable y fechas

### Menús de Navegación
```
Contabilidad
├── Control de Cierre
│   ├── Operaciones
│   │   ├── Hojas de Cierre
│   │   └── Crear Hoja de Cierre
│   └── Configuración
│       └── Plantillas de Cierre
```

## 📊 Ejemplos de Uso

### Plantilla Mensual Estándar
Incluye tareas típicas de cierre mensual:
1. **Conciliación Bancaria** (Manual)
2. **Revisión de Inventarios** (Manual)
3. **Validar Cuentas Puente** (Python automático)
4. **Provisiones y Ajustes** (Manual)
5. **Validación de Balance** (Python automático)

### Plantilla Anual Completa
Extiende la mensual con tareas adicionales:
6. **Inventario Físico Completo** (Manual)
7. **Revisión de Activos Fijos** (Manual)
8. **Cálculo de Impuestos Anuales** (Manual)

## 🚀 Instalación y Configuración

### Requisitos
- Odoo 18.0
- Módulo `account` (Contabilidad)

### Pasos de Instalación
1. Copiar el módulo a la carpeta de addons
2. Actualizar lista de aplicaciones
3. Instalar "Account Closing Control"
4. Configurar plantillas de cierre según necesidades

### Configuración Inicial
1. **Crear plantillas** desde Contabilidad → Configuración → Plantillas de Cierre
2. **Definir tareas** con tipos de validación apropiados
3. **Configurar códigos Python** para validaciones automáticas
4. **Asignar responsabilidades** por grupo de usuarios
5. **Probar el flujo** con un cierre de prueba

## 🔍 Validaciones Python Personalizables

### Ejemplos de Validaciones

#### Verificar Cuentas con Saldo Específico
```python
# Verificar que cuentas de caja tengan saldo positivo
cash_accounts = env['account.account'].search([('code', 'like', '1101%')])
for account in cash_accounts:
    if account.balance < 0:
        raise UserError(f"Cuenta de caja {account.code} con saldo negativo: {account.balance}")
```

#### Validar Conciliaciones Bancarias
```python
# Verificar que todas las cuentas bancarias estén conciliadas
bank_accounts = env['account.account'].search([('account_type', '=', 'asset_current'), ('code', 'like', '1102%')])
for account in bank_accounts:
    unreconciled = env['account.move.line'].search([
        ('account_id', '=', account.id),
        ('reconciled', '=', False),
        ('date', '<=', date_to)
    ])
    if unreconciled:
        raise UserError(f"Cuenta {account.code} tiene {len(unreconciled)} movimientos sin conciliar")
```

#### Verificar Inventarios
```python
# Verificar que no hay movimientos de inventario pendientes
pending_moves = env['stock.move'].search([
    ('date', '<=', date_to),
    ('state', 'not in', ['done', 'cancel'])
])
if pending_moves:
    raise UserError(f"Hay {len(pending_moves)} movimientos de inventario pendientes")
```

## 📈 Beneficios del Módulo

### Para Analistas Contables
- **Guía estructurada** para el proceso de cierre
- **Instrucciones claras** para cada tarea
- **Seguimiento visual** del progreso
- **Documentación automática** del trabajo realizado

### Para Gerentes Contables
- **Control total** sobre el proceso de aprobación
- **Visibilidad completa** del estado de cierres
- **Reportes profesionales** para auditoría
- **Trazabilidad** de cambios y responsables

### Para la Organización
- **Estandarización** de procesos contables
- **Reducción de errores** mediante validaciones automáticas
- **Cumplimiento** de controles internos
- **Auditoría** facilitada con documentación completa

## 🛠️ Mantenimiento y Extensiones

### Agregar Nuevas Validaciones
1. Editar plantilla de cierre existente
2. Crear nueva línea con tipo "Python"
3. Escribir código de validación en el campo correspondiente
4. Probar la validación en un cierre de prueba

### Personalizar Plantillas
- Las plantillas son completamente configurables
- Se pueden agregar, modificar o eliminar tareas según necesidades
- Cada empresa puede tener sus propias plantillas personalizadas

### Integración con Otros Módulos
El módulo está diseñado para integrarse fácilmente con:
- Módulos de inventario para validaciones automáticas
- Módulos de nómina para provisiones
- Módulos de activos fijos para depreciaciones
- Módulos de presupuesto para análisis de variaciones

## 📋 Checklist de Implementación

- [ ] Instalar el módulo en entorno de desarrollo
- [ ] Configurar plantillas básicas (mensual, anual)
- [ ] Definir tareas específicas de la organización
- [ ] Escribir validaciones Python personalizadas
- [ ] Probar el flujo completo con datos de prueba
- [ ] Capacitar usuarios en el nuevo proceso
- [ ] Implementar en producción
- [ ] Documentar procedimientos específicos de la empresa

---

**Desarrollado por**: Financial Toolkit Team  
**Versión**: 18.0.1.0.0  
**Licencia**: LGPL-3  
**Soporte**: https://github.com/zanello1234/partner_expense_account