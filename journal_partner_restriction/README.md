# Journal Partner Restriction

**Versión:** 18.0.1.0.0  
**Compatibilidad:** Odoo 18.0  
**Licencia:** LGPL-3  

## 📋 Descripción

Este módulo permite restringir qué partners pueden ser seleccionados al crear facturas de cliente o facturas de proveedor basándose en la configuración del journal. Es especialmente útil para organizaciones que necesitan controlar qué proveedores o clientes pueden ser utilizados con journals específicos por razones de seguridad, compliance o control interno.

## ✨ Características Principales

### 🔒 Control de Acceso por Journal
- **Restricción configurable**: Cada journal puede habilitar/deshabilitar restricciones de partners independientemente
- **Selección granular**: Especifica exactamente qué partners están permitidos por journal
- **Aplicación automática**: Las restricciones se aplican automáticamente al crear/editar facturas

### 🎯 Filtrado Inteligente
- **Filtrado dinámico**: La lista de partners se actualiza automáticamente al cambiar el journal
- **Validación en tiempo real**: Advertencias inmediatas si seleccionas un partner no permitido
- **Tipos de movimiento**: Respeta automáticamente la diferencia entre clientes y proveedores

### 🛡️ Validaciones Robustas
- **Validación de formulario**: Impide la selección de partners no autorizados en la interfaz
- **Validación de base de datos**: Constrains que previenen guardar registros inválidos
- **Mensajes informativos**: Alertas claras sobre las restricciones activas

## 🚀 Instalación

### Desde la Interfaz de Odoo
1. Ve a **Aplicaciones** en el menú principal
2. Busca "Journal Partner Restriction"
3. Haz clic en **Instalar**

### Instalación Manual
1. Descarga o clona este repositorio
2. Copia la carpeta `journal_partner_restriction` a tu directorio de addons
3. Reinicia el servidor Odoo
4. Actualiza la lista de aplicaciones
5. Instala el módulo

## ⚙️ Configuración

### Paso 1: Acceder a la Configuración
1. Ve a **Contabilidad > Configuración > Journals**
2. Selecciona el journal que deseas configurar
3. Haz clic en la pestaña **"Partner Restrictions"**

### Paso 2: Habilitar Restricciones
1. Marca la casilla **"Restrict Partners"**
2. Selecciona los partners permitidos en **"Allowed Partners"**
3. Guarda los cambios

### Configuración Avanzada
- **Partners múltiples**: Puedes agregar tantos partners como necesites
- **Modificación en cualquier momento**: Las restricciones se pueden cambiar incluso con facturas existentes
- **Journals sin restricciones**: Los journals que no tengan restricciones funcionarán normalmente

## 📖 Uso Detallado

### Creación de Facturas con Restricciones

#### Facturas de Cliente (out_invoice)
1. Ve a **Contabilidad > Clientes > Facturas**
2. Crea una nueva factura
3. Selecciona un journal con restricciones configuradas
4. El campo "Cliente" mostrará solo los partners permitidos para ese journal
5. Si el journal no tiene partners configurados, se mostrará una advertencia

#### Facturas de Proveedor (in_invoice)
1. Ve a **Contabilidad > Proveedores > Facturas**
2. Crea una nueva factura
3. Selecciona un journal con restricciones
4. Solo aparecerán los proveedores autorizados para ese journal

### Comportamiento del Sistema

#### Al Cambiar Journal
- **Actualización automática**: La lista de partners se filtra inmediatamente
- **Validación de partner actual**: Si el partner seleccionado no está permitido, se limpia automáticamente
- **Mensaje de advertencia**: Se muestra una alerta explicando el cambio

#### Validaciones en Tiempo Real
- **Advertencia visual**: Aparece un banner informativo cuando hay restricciones activas
- **Lista de partners permitidos**: Se muestra qué partners están disponibles
- **Prevención de errores**: No permite guardar con partners no autorizados

## 🔧 Funcionalidades Técnicas

### Arquitectura
- **Campos computados**: `allowed_partner_ids` se calcula dinámicamente
- **Métodos onchange**: Filtrado en tiempo real al cambiar journal o tipo de factura
- **Validaciones constrains**: Protección a nivel de base de datos
- **Interfaz responsiva**: UI que se adapta a las restricciones configuradas

### Integración con Odoo Core
- **Herencia limpia**: Extiende modelos existentes sin conflictos
- **Compatibilidad**: Funciona con otros módulos de contabilidad
- **Performance optimizada**: Búsquedas eficientes con límites razonables

## 🎨 Interfaz de Usuario

### Vista de Journal
- **Pestaña dedicada**: "Partner Restrictions" separada del resto de configuraciones
- **Interfaz intuitiva**: Checkbox simple para habilitar/deshabilitar
- **Selector visual**: Widget de tags para seleccionar partners
- **Ayuda contextual**: Textos explicativos sobre el funcionamiento

### Vista de Facturas
- **Filtrado transparente**: Los partners se filtran sin intervención del usuario
- **Alertas informativas**: Banners que explican las restricciones activas
- **Feedback inmediato**: Mensajes de error claros cuando hay problemas

## 📊 Casos de Uso

### Control de Compliance
- **Segregación de proveedores**: Diferentes journals para diferentes tipos de gastos
- **Control de autorización**: Solo ciertos proveedores para gastos específicos
- **Auditoría**: Registro claro de qué partners pueden usar cada journal

### Organización Interna
- **Departamentos**: Journals específicos para diferentes departamentos
- **Proyectos**: Restricciones por proyecto o centro de costos
- **Geografía**: Partners específicos por región o país

### Seguridad
- **Prevención de errores**: Evita seleccionar partners incorrectos
- **Control de acceso**: Limita qué partners pueden ser utilizados
- **Trazabilidad**: Registro de configuraciones y cambios

## 🛠️ Solución de Problemas

### Problemas Comunes

#### "No aparecen partners en la lista"
- **Causa**: Journal tiene restricciones habilitadas pero sin partners configurados
- **Solución**: Ve a la configuración del journal y agrega partners permitidos

#### "Mi partner habitual no aparece"
- **Causa**: El partner no está en la lista de permitidos para ese journal
- **Solución**: Agrega el partner a la configuración del journal o usa un journal diferente

#### "Las restricciones no se aplican"
- **Causa**: El módulo necesita ser actualizado después de cambios
- **Solución**: Actualiza el módulo desde Aplicaciones

### Logs y Debugging
Para activar logs detallados, agrega este contexto en la consola de desarrollador:
```python
move = self.env['account.move'].with_context(debug_partner_restriction=True)
```

## 🔄 Actualizaciones y Mantenimiento

### Modificar Restricciones
- Las restricciones se pueden modificar en cualquier momento
- Los cambios se aplican inmediatamente
- No afecta facturas ya creadas

### Backup de Configuración
- Las configuraciones se guardan en la base de datos
- Se incluyen en backups normales de Odoo
- Portables entre instancias

## 👥 Soporte y Contribuciones

### Reportar Problemas
Si encuentras algún problema:
1. Verifica que estés usando Odoo 18.0
2. Revisa la configuración del journal
3. Busca mensajes de error en los logs
4. Reporta el issue con pasos detallados para reproducirlo

### Mejoras y Sugerencias
Las contribuciones son bienvenidas:
- Fork del repositorio
- Crea una rama para tu feature
- Implementa los cambios con tests
- Crea un pull request con descripción detallada

## 📋 Dependencias

### Requeridas
- **account**: Módulo base de contabilidad de Odoo

### Compatibilidad Verificada
- ✅ Odoo 18.0 Community Edition
- ✅ Odoo 18.0 Enterprise Edition
- ✅ Módulos de localización contable
- ✅ Otros módulos de contabilidad estándar

## 📄 Licencia

Este módulo se distribuye bajo la licencia **LGPL-3**. Consulta el archivo LICENSE para más detalles.

## 🏗️ Autor

**Desarrollado por:** Tu Empresa  
**Versión inicial:** 18.0.1.0.0  
**Fecha de creación:** Octubre 2025  

---

**¿Necesitas ayuda?** Consulta la documentación de Odoo o contacta con el soporte técnico.