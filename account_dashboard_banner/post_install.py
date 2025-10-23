# Copyright 2025 Akretion France (https://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

_logger = logging.getLogger(__name__)

# I create default cells via post-install script instead of
# data/account_dashboard_banner_cell.xml
# to avoid the problem when a user deletes a cell that has an XMLID
# and Odoo would re-create the cells when the module is reloaded
def create_default_account_dashboard_cells(env):
    # Crear KPIs básicos sin configuración CTA (eliminado)
    vals_list = [
        {"cell_type": "hard_lock_date", "sequence": 10, "warn": True, "active_in_dashboard": True, "category": "lock_dates", "click_action": "none"},
        {"cell_type": "income_fiscalyear", "sequence": 20, "active_in_dashboard": True, "category": "financial", "click_action": "account_move"},
        {"cell_type": "customer_overdue", "sequence": 30, "active_in_dashboard": True, "category": "receivables", "click_action": "res_partner"},
        {"cell_type": "customer_debt", "sequence": 40, "active_in_dashboard": True, "category": "receivables", "click_action": "res_partner"},
        {"cell_type": "supplier_debt", "sequence": 50, "active_in_dashboard": True, "category": "payables", "click_action": "res_partner"},
        
        # Liquidez general (todas las cuentas)
        {"cell_type": "liquidity", "sequence": 60, "warn": True, "warn_type": "under", "active_in_dashboard": True, "category": "liquidity", "click_action": "account_account", "liquidity_mode": "all_accounts"},
        
        {"cell_type": "total_assets", "sequence": 70, "active_in_dashboard": True, "category": "financial", "click_action": "account_account"},
        {"cell_type": "total_liabilities", "sequence": 80, "active_in_dashboard": True, "category": "financial", "click_action": "account_account"},
        {"cell_type": "oldest_customer_invoice", "sequence": 90, "warn": True, "warn_type": "above", "warn_max": 30, "active_in_dashboard": True, "category": "aging", "click_action": "account_move"},
        {"cell_type": "oldest_supplier_invoice", "sequence": 100, "warn": True, "warn_type": "above", "warn_max": 30, "active_in_dashboard": True, "category": "aging", "click_action": "account_move"},
        {"cell_type": "receivable_payable_ratio", "sequence": 110, "warn": True, "warn_type": "outside", "warn_min": 0.5, "warn_max": 2.0, "active_in_dashboard": True, "category": "ratios", "click_action": "none"},
        
        # KPIs de Contadores
        {"cell_type": "customer_invoices_count", "sequence": 115, "warn": True, "warn_type": "outside", "warn_min": 5, "warn_max": 1000, "active_in_dashboard": True, "category": "performance", "click_action": "account_move"},
        {"cell_type": "supplier_bills_count", "sequence": 116, "warn": True, "warn_type": "outside", "warn_min": 1, "warn_max": 500, "active_in_dashboard": True, "category": "performance", "click_action": "account_move"},
        
        # KPIs de Rentabilidad básicos
        {"cell_type": "ebit", "sequence": 120, "active_in_dashboard": True, "category": "profitability", "click_action": "account_move"},
        {"cell_type": "ebit_ratio", "sequence": 130, "warn": True, "warn_type": "under", "warn_min": 5.0, "active_in_dashboard": True, "category": "profitability", "click_action": "account_move"},
        {"cell_type": "gross_income", "sequence": 135, "warn": True, "warn_type": "under", "active_in_dashboard": True, "category": "profitability", "click_action": "account_move"},
        {"cell_type": "nopat", "sequence": 140, "active_in_dashboard": True, "category": "profitability", "click_action": "account_move"},
        
        # KPIs de Ratios Avanzados
        {"cell_type": "cost_income_ratio", "sequence": 145, "warn": True, "warn_type": "above", "warn_max": 70.0, "active_in_dashboard": True, "category": "ratios", "click_action": "account_move"},
        {"cell_type": "ebit_assets_ratio", "sequence": 150, "warn": True, "warn_type": "under", "warn_min": 10.0, "active_in_dashboard": True, "category": "ratios", "click_action": "account_move"},
    ]
    
    # Crear los KPIs básicos
    dashboard_cells = env["account.dashboard.banner.cell"].create(vals_list)
    
    # Crear KPIs específicos para cada cuenta de liquidez
    create_liquidity_kpis_per_account(env)

def create_liquidity_kpis_per_account(env):
    """Crear KPIs de liquidez individuales por cuenta bancaria/efectivo"""
    _logger.info("Creando KPIs de liquidez por cuenta individual...")
    
    # Buscar todas las cuentas de liquidez (caja y banco) en todas las compañías
    liquidity_journals = env['account.journal'].search([
        ('type', 'in', ('bank', 'cash')),
        ('default_account_id', '!=', False),
    ])
    
    sequence_start = 160  # Empezar después de los otros KPIs
    
    for journal in liquidity_journals:
        account = journal.default_account_id
        if not account:
            continue
            
        # Crear nombre personalizado más descriptivo
        account_type_label = "Efectivo" if journal.type == 'cash' else "Banco"
        custom_label = f"Liquidez - {account.name} ({account.code})"
        if journal.company_id:
            custom_label += f" - {journal.company_id.name}"
        
        # Crear tooltip descriptivo
        custom_tooltip = f"Saldo de liquidez de la cuenta {account_type_label}: {account.name} ({account.code})"
        if journal.company_id:
            custom_tooltip += f" en {journal.company_id.name}"
        
        # Crear KPI específico para esta cuenta
        kpi_vals = {
            'cell_type': 'liquidity',
            'sequence': sequence_start,
            'custom_label': custom_label,
            'custom_tooltip': custom_tooltip,
            'warn': True,
            'warn_type': 'under',
            'warn_min': 1000.0,  # Alerta si es menor a 1000 en la moneda base
            'active_in_dashboard': True,
            'category': 'liquidity',
            'click_action': 'account_account',
            'action_domain': f"[('id', '=', {account.id})]",  # Filtrar por esta cuenta específica
            'liquidity_mode': 'specific_accounts',
            'specific_account_ids': [(6, 0, [account.id])],
        }
        
        # Verificar que no exista ya un KPI igual
        existing_kpi = env["account.dashboard.banner.cell"].search([
            ('cell_type', '=', 'liquidity'),
            ('liquidity_mode', '=', 'specific_accounts'),
            ('specific_account_ids', 'in', [account.id]),
        ])
        
        if not existing_kpi:
            env["account.dashboard.banner.cell"].create(kpi_vals)
            sequence_start += 1
