# Account Partner Assignment

## Descripción

Este módulo para Odoo 18 permite asignar uno o más partners (contactos) a cuentas por pagar o por cobrar directamente desde el plan de cuentas. Cuando se asigna un partner a una cuenta contable, automáticamente se actualiza la configuración de la cuenta por defecto en la ficha del partner.

## Características

- ✅ Asignación de múltiples partners a cuentas de tipo "Por cobrar" (asset_receivable)
- ✅ Asignación de múltiples partners a cuentas de tipo "Por pagar" (liability_payable)  
- ✅ Actualización automática de las cuentas por defecto en la ficha del partner
- ✅ Wizard para gestión masiva de asignaciones
- ✅ Validaciones para evitar asignaciones incorrectas
- ✅ Vista especializada para cuentas con partners asignados
- ✅ Campo de solo lectura en partners para ver sus cuentas asignadas

## Instalación

1. Copiar el módulo `account_partner_assignment` al directorio de addons de Odoo
2. Actualizar la lista de módulos
3. Instalar el módulo desde Aplicaciones

## Uso

### Desde el Plan de Cuentas

1. Ir a **Contabilidad → Configuración → Plan de Cuentas**
2. Abrir una cuenta de tipo "Por cobrar" o "Por pagar"
3. En el campo **"Partners Asignados"** seleccionar los contactos deseados
4. Guardar - Los partners se actualizarán automáticamente

### Usando el Wizard de Asignación

1. Desde una cuenta contable, hacer clic en **"Assign Partners"**
2. Seleccionar la acción deseada:
   - **Agregar Partners**: Añadir nuevos partners a los existentes
   - **Reemplazar Todos**: Reemplazar todos los partners asignados
   - **Remover Partners**: Quitar partners específicos
3. Seleccionar los partners y confirmar

### Vista Especializada

Acceder a **Contabilidad → Configuración → Partner Account Assignment** para una vista dedicada de cuentas por pagar/cobrar con sus partners asignados.

## Funcionalidades Técnicas

### Modelos Extendidos

- **account.account**: Añade campo `assigned_partner_ids` y lógica de sincronización
- **res.partner**: Añade campo `assigned_account_ids` (solo lectura)

### Validaciones

- Solo permite asignación en cuentas de tipo `asset_receivable` y `liability_payable`
- Previene asignaciones incorrectas mediante constrains

### Automatización

- Al asignar un partner a una cuenta por cobrar → actualiza `property_account_receivable_id`
- Al asignar un partner a una cuenta por pagar → actualiza `property_account_payable_id`

## Seguridad

- **Managers de Contabilidad**: Acceso completo
- **Usuarios de Contabilidad**: Solo lectura y creación (sin eliminación de asignaciones)

## Requisitos

- Odoo 18.0
- Módulo `account` (incluido en instalación base)

## Autor

Desarrollado para gestión eficiente de relaciones partner-cuenta en Odoo 18.

## Licencia

LGPL-3