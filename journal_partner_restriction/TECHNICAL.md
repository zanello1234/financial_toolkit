# Documentación Técnica - Journal Partner Restriction

## Arquitectura del Módulo

### Estructura de Archivos

```
journal_partner_restriction/
├── __init__.py                     # Inicialización del módulo
├── __manifest__.py                 # Metadatos y configuración
├── README.md                       # Documentación de usuario
├── models/
│   ├── __init__.py                # Inicialización de modelos
│   ├── account_journal.py         # Extensión del modelo journal
│   └── account_move.py            # Extensión del modelo move
├── views/
│   ├── account_journal_views.xml  # Vistas de configuración
│   └── account_move_views.xml     # Vistas de facturas
├── security/
│   └── ir.model.access.csv        # Permisos de acceso
└── demo/
    └── demo_data.xml              # Datos de demostración
```

### Modelos Extendidos

#### 1. account.journal

**Nuevos campos agregados:**

```python
restrict_partners = fields.Boolean(
    string='Restrict Partners',
    help='If enabled, only selected partners can be used with this journal',
    default=False
)

allowed_partner_ids = fields.Many2many(
    'res.partner',
    'journal_partner_rel',
    'journal_id',
    'partner_id',
    string='Allowed Partners',
    help='Partners that can be used with this journal when restriction is enabled'
)
```

**Métodos sobrescritos:**
- `_check_journal_lock()`: Permite modificar restricciones incluso con entradas contabilizadas
- `write()`: Manejo especial para campos de restricción

#### 2. account.move

**Nuevos campos agregados:**

```python
allowed_partner_ids = fields.Many2many(
    'res.partner',
    string='Allowed Partners',
    compute='_compute_allowed_partner_ids',
    store=False
)
```

**Métodos implementados:**

##### `_compute_allowed_partner_ids()`
```python
@api.depends('journal_id', 'move_type')
def _compute_allowed_partner_ids(self):
    """
    Calcula dinámicamente qué partners están permitidos
    basándose en el journal y el tipo de movimiento.
    """
```

##### `_onchange_journal_id_partner_restriction()`
```python
@api.onchange('journal_id')
def _onchange_journal_id_partner_restriction(self):
    """
    Actualiza el dominio de partners cuando cambia el journal.
    Retorna dominio dinámico y validaciones.
    """
```

##### `_check_partner_journal_restriction()`
```python
@api.constrains('partner_id', 'journal_id')
def _check_partner_journal_restriction(self):
    """
    Validación a nivel de base de datos que impide
    guardar partners no autorizados.
    """
```

## Flujo de Datos

### Configuración de Restricciones

1. **Usuario accede** a journal → Pestaña "Partner Restrictions"
2. **Habilita restricción** → `restrict_partners = True`
3. **Selecciona partners** → `allowed_partner_ids` se actualiza
4. **Configuración se guarda** → Disponible para facturas

### Aplicación de Restricciones

1. **Usuario crea factura** → Vista de account.move
2. **Selecciona journal** → Trigger `@api.onchange('journal_id')`
3. **Se calcula dominio** → `_compute_allowed_partner_ids()`
4. **Se aplica filtro** → Solo partners permitidos visibles
5. **Validación final** → `@api.constrains` al guardar

## Integración con Vistas

### Vista de Journal (account_journal_views.xml)

```xml
<xpath expr="//notebook" position="inside">
    <page string="Partner Restrictions" name="partner_restrictions">
        <group>
            <group string="Configuration">
                <field name="restrict_partners"/>
                <!-- Campos y ayuda contextual -->
            </group>
        </group>
    </page>
</xpath>
```

**Características:**
- Pestaña separada para mejor organización
- Campos condicionales que aparecen/desaparecen
- Textos de ayuda explicativos
- Widget optimizado para selección múltiple

### Vista de Move (account_move_views.xml)

```xml
<xpath expr="//field[@name='partner_id']" position="before">
    <field name="allowed_partner_ids" invisible="1"/>
</xpath>
<xpath expr="//field[@name='partner_id']" position="attributes">
    <attribute name="domain">[('id', 'in', allowed_partner_ids)]</attribute>
</xpath>
```

**Características:**
- Campo computado invisible para el dominio
- Aplicación automática del filtro
- Alertas contextuales cuando hay restricciones
- Integración transparente con el flujo existente

## Consideraciones de Performance

### Optimizaciones Implementadas

1. **Campo computado no almacenado**: `store=False` para `allowed_partner_ids`
2. **Búsquedas limitadas**: Límite de 1000 registros para journals sin restricciones
3. **Dependencias específicas**: `@api.depends('journal_id', 'move_type')`
4. **Filtrado eficiente**: Uso de listas de IDs en lugar de búsquedas complejas

### Impacto en Base de Datos

- **Nueva tabla**: `journal_partner_rel` para la relación Many2many
- **Sin campos adicionales en tablas core**: Solo extends existing models
- **Índices automáticos**: Odoo maneja la indexación de las relaciones

## Seguridad y Permisos

### Archivo: security/ir.model.access.csv

```csv
id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_account_journal_partner_restriction,access_account_journal_partner_restriction,account.model_account_journal,account.group_account_user,1,1,1,1
```

**Niveles de acceso:**
- **account.group_account_user**: Acceso completo a la configuración
- **Hereda permisos**: De los modelos base account.journal y account.move

## Testing y Validación

### Datos de Demostración

El archivo `demo/demo_data.xml` incluye:

```xml
<!-- Partners de prueba -->
<record id="demo_partner_supplier_1" model="res.partner">
    <field name="name">Restricted Supplier 1</field>
    <field name="supplier_rank">1</field>
</record>

<!-- Journals configurados con restricciones -->
<record id="demo_purchase_journal_restricted" model="account.journal">
    <field name="restrict_partners" eval="True"/>
    <field name="allowed_partner_ids" eval="[(6, 0, [ref('demo_partner_supplier_1')])]"/>
</record>
```

### Escenarios de Prueba

1. **Configuración básica**:
   - Habilitar/deshabilitar restricciones
   - Agregar/remover partners permitidos
   - Guardar configuración con facturas existentes

2. **Creación de facturas**:
   - Journal sin restricciones → Todos los partners disponibles
   - Journal con restricciones → Solo partners permitidos
   - Cambio de journal → Actualización automática del dominio

3. **Validaciones**:
   - Intentar guardar partner no permitido → Error de validación
   - Partner válido → Guardado exitoso
   - Cambio de configuración → Aplicación inmediata

## Resolución de Problemas Técnicos

### Debug Mode

Para activar logs detallados:

```python
# En consola de Odoo
move = self.env['account.move'].with_context(debug_partner_restriction=True)
```

### Logs Disponibles

El módulo incluye prints de debug que muestran:
- Cambios de journal
- Estado de restricciones
- Partners calculados
- Dominios aplicados

### Problemas Conocidos y Soluciones

1. **Campo computado no se actualiza**:
   - Causa: Cache de Odoo
   - Solución: El módulo maneja esto automáticamente con `@api.depends`

2. **Restricciones no se aplican en API**:
   - Causa: Las validaciones onchange no se ejecutan en llamadas API
   - Solución: Los `@api.constrains` protegen a nivel de base de datos

3. **Performance lenta con muchos partners**:
   - Causa: Búsquedas sin límite
   - Solución: Implementado límite de 1000 registros

## Compatibilidad y Actualizaciones

### Versiones de Odoo Soportadas
- ✅ **18.0**: Completamente compatible y probado
- ⚠️ **17.0**: Requiere adaptaciones menores (sintaxis de attrs)
- ❌ **16.0 y anteriores**: No compatible sin modificaciones significativas

### Migración de Versiones

Para migrar a versiones futuras:
1. Actualizar dependencias en `__manifest__.py`
2. Verificar sintaxis de vistas (attrs vs invisible/required)
3. Probar métodos API (pueden cambiar signatures)
4. Validar compatibilidad de widgets

## Extensibilidad

### Puntos de Extensión

El módulo está diseñado para ser extensible:

1. **Nuevos tipos de restricción**:
   ```python
   # Ejemplo: Restricción por fecha
   date_restriction = fields.Boolean()
   allowed_date_range = fields.Date()
   ```

2. **Validaciones adicionales**:
   ```python
   @api.constrains('partner_id', 'journal_id', 'custom_field')
   def _check_custom_restriction(self):
       # Lógica personalizada
   ```

3. **Filtros personalizados**:
   ```python
   def _get_custom_partner_domain(self):
       # Lógica de dominio personalizada
   ```

### Hooks Disponibles

- `_compute_allowed_partner_ids()`: Override para lógica personalizada
- `_onchange_journal_id_partner_restriction()`: Extend para validaciones adicionales
- `_check_partner_journal_restriction()`: Extend para constraints personalizados

---

Esta documentación técnica proporciona todos los detalles necesarios para entender, mantener y extender el módulo Journal Partner Restriction.