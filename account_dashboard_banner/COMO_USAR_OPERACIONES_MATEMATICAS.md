# 🧮 Cómo Usar las Operaciones Matemáticas entre KPIs

## 📍 **Dónde encontrar la funcionalidad**

### **Paso 1: Acceder al módulo**
1. Ve a **Contabilidad** → **Configuración** → **Dashboard Banner Cells**
2. O busca "Dashboard Banner" en la barra de búsqueda de Odoo

### **Paso 2: Crear un nuevo KPI matemático**
1. Haz clic en **"Crear"** para agregar un nuevo KPI
2. En el campo **"Cell Type"** (Tipo de Celda), selecciona:
   **"Mathematical Operation Between KPIs"**

### **Paso 3: Configurar la operación matemática**
Una vez que selecciones el tipo "Mathematical Operation Between KPIs", aparecerá una nueva sección llamada:

**"Mathematical Operations Configuration"**

En esta sección verás:

#### **📊 Campos de configuración:**

1. **Mathematical Operation** (Operación Matemática):
   - 🔘 Addition (+) - Suma
   - 🔘 Subtraction (-) - Resta  
   - 🔘 Multiplication (×) - Multiplicación
   - 🔘 Division (÷) - División
   - 🔘 Percentage - Porcentaje (A/B * 100%)

2. **First KPI (A)** (Primer KPI):
   - Selector desplegable con todos los KPIs disponibles
   - No puedes seleccionar el mismo KPI que estás creando

3. **Second KPI (B)** (Segundo KPI):
   - Selector desplegable con todos los KPIs disponibles
   - No puede ser igual al Primer KPI
   - No puedes seleccionar el mismo KPI que estás creando

4. **Decimal Places** (Lugares Decimales):
   - Número de decimales a mostrar en el resultado
   - Por defecto: 2

## 🎯 **Ejemplo práctico: Crear un KPI de Margen de Beneficio**

### **Escenario:** 
Quieres crear un KPI que calcule: `(Beneficio ÷ Ventas) × 100%`

### **Pasos:**

1. **Crear nuevo KPI**:
   - Cell Type: `"Mathematical Operation Between KPIs"`
   - Custom Label: `"Margen de Beneficio"`

2. **Configurar operación**:
   - Mathematical Operation: `Percentage`
   - First KPI (A): Selecciona tu KPI de "Beneficio Neto"  
   - Second KPI (B): Selecciona tu KPI de "Ventas Totales"
   - Decimal Places: `2`

3. **Guardar**: El KPI aparecerá en tu dashboard mostrando el porcentaje calculado

## 🔍 **¿No ves la sección de configuración?**

### **Posibles causas:**

1. **Cell Type incorrecto**: Asegúrate de seleccionar exactamente `"Mathematical Operation Between KPIs"`

2. **Cache del navegador**: Refresca la página (Ctrl+F5)

3. **Permisos**: Verifica que tengas permisos de administrador

4. **Módulo no actualizado**: Puede que necesites actualizar el módulo:
   - Ve a Apps → Busca "Account Dashboard Banner"
   - Haz clic en "Actualizar"

## 📋 **Lista de verificación**

- ✅ Cell Type = "Mathematical Operation Between KPIs"
- ✅ Aparece sección "Mathematical Operations Configuration"  
- ✅ Campos visibles: Operation, First KPI, Second KPI, Decimal Places
- ✅ Mensaje de ayuda explicando cada operación

## 🚨 **Si aún no aparece**

Si después de seguir estos pasos no ves la configuración, es posible que haya un problema de cache o que necesites reiniciar el servidor de Odoo.

**Soluciones:**
1. Refresca completamente la página (Ctrl+Shift+R)
2. Cierra y vuelve a abrir la pestaña
3. Verifica que el módulo esté correctamente instalado y actualizado

¿En qué paso específicamente tienes problemas? ¿Ves el tipo de KPI "Mathematical Operation Between KPIs" en la lista de opciones?