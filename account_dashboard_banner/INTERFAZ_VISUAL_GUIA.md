# 🖥️ Interfaz Visual: Operaciones Matemáticas entre KPIs

## 📸 **Cómo debería verse la interfaz**

Cuando crees o edites un KPI y selecciones el tipo correcto, deberías ver algo como esto:

```
┌─────────────────────────────────────────────────────┐
│                    KPI Configuration                │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Cell Type: [Mathematical Operation Between KPIs ▼] │
│                                                     │
│ Custom Label: [_________________________]          │
│                                                     │
│ ═══════════════════════════════════════════════════ │
│     Mathematical Operations Configuration           │
│ ═══════════════════════════════════════════════════ │
│                                                     │
│ Mathematical Operation:                             │
│ ○ Addition (+)                                      │
│ ○ Subtraction (-)                                   │
│ ○ Multiplication (×)                                │
│ ● Division (÷)                  ← Seleccionado     │
│ ○ Percentage                                        │
│                                                     │
│ First KPI (A): [Ventas Totales           ▼]       │
│                                                     │
│ Second KPI (B): [Costos de Ventas        ▼]       │
│                                                     │
│ Decimal Places: [2____]                            │
│                                                     │
│ ┌─ Mathematical Operations: ──────────────────────┐ │
│ │ • Addition (+): KPI A + KPI B                  │ │
│ │ • Subtraction (-): KPI A - KPI B               │ │
│ │ • Multiplication (×): KPI A × KPI B            │ │
│ │ • Division (÷): KPI A ÷ KPI B                  │ │
│ │ • Percentage: (KPI A ÷ KPI B) × 100%           │ │
│ │ Choose two different KPIs to perform...        │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

## 🔍 **Pasos detallados para encontrar la funcionalidad:**

### **1. Navegación en Odoo:**
```
Menú principal → Contabilidad → Configuración → Dashboard Banner Cells
```

### **2. Crear nuevo KPI:**
```
Botón "Crear" (en la parte superior izquierda)
```

### **3. Seleccionar tipo correcto:**
En el campo "Cell Type", busca y selecciona:
```
"Mathematical Operation Between KPIs"
```

**⚠️ Nota importante:** El texto exacto puede variar según el idioma de tu instalación de Odoo.

### **4. Verificar aparición de campos:**
Después de seleccionar el tipo, automáticamente debería aparecer la sección:
```
"Mathematical Operations Configuration"
```

## 🚨 **Troubleshooting (Solución de problemas):**

### **Problema 1: No veo el tipo de KPI**
**Posible causa:** El módulo no está actualizado
**Solución:**
1. Ve a `Apps` (Aplicaciones)
2. Busca "Account Dashboard Banner"  
3. Si aparece "Actualizar", haz clic
4. Si no aparece, puede que necesites reinstalar el módulo

### **Problema 2: Veo el tipo pero no los campos**
**Posible causa:** Cache del navegador
**Solución:**
1. Presiona `Ctrl + Shift + R` para refrescar completamente
2. Cierra y vuelve a abrir la pestaña
3. Prueba en modo incógnito/privado

### **Problema 3: Error al guardar**
**Posible causa:** Validaciones no cumplidas
**Solución:**
1. Asegúrate de seleccionar ambos KPIs (A y B)
2. Verifica que sean diferentes entre sí
3. Selecciona una operación matemática

## 🎯 **¿Exactamente qué ves en tu pantalla?**

Para ayudarte mejor, ¿podrías decirme:

1. ¿Ves el tipo de KPI "Mathematical Operation Between KPIs" en la lista desplegable?
2. ¿Cuando lo seleccionas, aparece alguna sección nueva?
3. ¿Qué versión de Odoo estás usando?
4. ¿Hay algún mensaje de error?

Con esta información podré ayudarte de manera más específica.