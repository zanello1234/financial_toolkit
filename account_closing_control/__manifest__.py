# -*- coding: utf-8 -*-
{
    'name': 'Account Closing Control',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Sistematización y control del proceso de cierre contable mensual y anual',
    'description': """
Account Closing Control - Control de Cierre Contable
=====================================================

Este módulo permite sistematizar, auditar y controlar el proceso de cierre contable 
mensual y anual a través de:

Funcionalidades Principales:
----------------------------
* **Plantillas de Cierre**: Define checklists reutilizables para diferentes tipos de cierre
* **Hojas de Cierre**: Instancias de trabajo para períodos específicos  
* **Validaciones Automáticas**: Ejecuta controles automáticos sobre la contabilidad
* **Bloqueo Seguro**: Bloquea períodos contables al finalizar el cierre
* **Trazabilidad**: Registro completo de quién, cuándo y por qué se realizaron cambios
* **Reportes de Auditoría**: Documentación formal del proceso de cierre

Tipos de Validaciones:
---------------------
* **Manual**: El analista confirma visualmente y marca como completado
* **Acción**: Enlaces directos a vistas de Odoo (ej: conciliación bancaria)
* **Python**: Validaciones automáticas personalizables por código

Control de Acceso:
-----------------
* **Analistas**: Pueden ejecutar tareas y enviar a revisión
* **Gerentes**: Pueden aprobar cierres y bloquear períodos
* **Asesores**: Control total sobre plantillas y configuración

Flujo de Trabajo:
----------------
1. Configurar plantillas de cierre reutilizables
2. Generar hoja de cierre para período específico
3. Ejecutar tareas del checklist (manual/automático)
4. Revisar y aprobar el cierre
5. Bloquear período contable automáticamente
6. Generar reporte de auditoría

Integración Contable:
--------------------
* Establece fechas de bloqueo contable (Account Lock Date)
* Establece fechas de bloqueo fiscal (Tax Lock Date)
* Mantiene integridad con el sistema contable de Odoo
    """,
    'author': 'Financial Toolkit',
    'website': 'https://github.com/zanello1234/partner_expense_account',
    'depends': ['account'],
    'data': [
        # Security
        'security/ir.model.access.csv',
        
        # Data
        'data/closing_template_data.xml',
        
        # Views
        'views/closing_template_views.xml',
        'views/closing_worksheet_views.xml',
        
        # Wizards
        'wizards/closing_wizard_views.xml',
        
        # Reports
        'reports/closing_report_templates.xml',
        'reports/closing_report_views.xml',
        
        # Menus
        'views/account_closing_menu.xml',
    ],
    'demo': [
        'demo/demo_closing_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}