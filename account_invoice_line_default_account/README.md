# Partner Expense Account - Odoo V18

Este módulo ha sido migrado de Odoo V16 a V18 y permite establecer cuentas contables por defecto para ingresos y gastos en cada partner.

## Funcionalidades

- Cuentas por defecto de ingresos y gastos en partners
- Auto-actualización de cuentas desde líneas de factura
- Configuración por partner para habilitar/deshabilitar auto-actualización

## Cambios en la migración a V18

- Actualización de la versión en `__manifest__.py` de 16.0 a 18.0
- Eliminación de dependencia `base_partition` (no compatible con V18)
- Actualización del código para usar métodos nativos de Python en lugar de `odoo.fields.first`
- Adaptación de dominios en campos Many2one para usar formato string
- Actualización de tests para compatibilidad con V18

## Instalación

1. Clonar este repositorio en tu directorio de addons
2. Actualizar la lista de módulos en Odoo
3. Instalar el módulo desde la interfaz de Odoo

## Uso

1. Ir a Contactos
2. Abrir un registro de partner
3. En la pestaña "Contabilidad", configurar:
   - Cuenta de Ingresos por Defecto
   - Cuenta de Gastos por Defecto
   - Checkboxes para habilitar auto-actualización

## Licencia

AGPL-3.0 or later