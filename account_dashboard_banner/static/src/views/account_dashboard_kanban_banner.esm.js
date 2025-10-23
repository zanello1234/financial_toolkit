/*
  Copyright 2025 Akretion France (https://www.akretion.com/)
  @author: Alexis de Lattre <alexis.delattre@akretion.com>
  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
*/

import {DashboardKanbanRecord} from "@account/views/account_dashboard_kanban/account_dashboard_kanban_record";
import {DashboardKanbanRenderer} from "@account/views/account_dashboard_kanban/account_dashboard_kanban_renderer";
import {kanbanView} from "@web/views/kanban/kanban_view";
import {onWillStart} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {useService} from "@web/core/utils/hooks";

export class DashboardKanbanRendererBanner extends DashboardKanbanRenderer {
    static template = "account_dashboard_banner.AccountDashboardBannerRenderer";
    static components = {
        ...DashboardKanbanRenderer.components,
        KanbanRecord: DashboardKanbanRecord,
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.actionService = useService("action");

        onWillStart(async () => {
            this.state.banner = await this.orm.call("account.dashboard.banner.cell", "get_dashboard_data_filtered");
        });
        
        // Hacer las funciones disponibles globalmente para el template
        window.navigateToKpiRecords = this.navigateToKpiRecords.bind(this);
        window.filterKpisByCategory = this.filterKpisByCategory.bind(this);
        window.openActivityForm = this.openActivityForm.bind(this);
        window.openKpiConfig = this.openKpiConfig.bind(this);
    }
    
    /**
     * Filter KPIs by category
     * @param {string} category - Category to filter by ('all' shows all)
     */
    filterKpisByCategory(category) {
        // Update active button
        document.querySelectorAll('.filter-buttons .btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.category === category) {
                btn.classList.add('active');
            }
        });
        
        // Filter KPI cards
        const kpiCards = document.querySelectorAll('.metric-tile-compact, .metric-tile-alert-compact');
        
        kpiCards.forEach(card => {
            const cardCategory = card.dataset.category;
            
            if (category === 'all' || cardCategory === category) {
                // Show card with animation
                card.classList.remove('kpi-hidden', 'kpi-fade-out');
                card.classList.add('kpi-fade-in');
                
                setTimeout(() => {
                    card.style.display = '';
                }, 50);
                
            } else {
                // Hide card with animation
                card.classList.remove('kpi-fade-in');
                card.classList.add('kpi-fade-out');
                
                setTimeout(() => {
                    card.classList.add('kpi-hidden');
                    card.style.display = 'none';
                }, 300);
            }
        });
        
        // Update grid layout after animation
        setTimeout(() => {
            const grid = document.querySelector('.metrics-grid-compact');
            if (grid) {
                grid.style.display = 'none';
                grid.offsetHeight; // Force reflow
                grid.style.display = 'grid';
            }
        }, 350);
    }
    
    /**
     * Navigate to records based on KPI click
     * @param {HTMLElement} element - The clicked KPI element
     */
    async navigateToKpiRecords(element) {
        try {
            const kpiType = element.dataset.kpiType;
            const clickAction = element.dataset.clickAction;
            const actionDomain = element.dataset.actionDomain;
            
            if (!kpiType || !clickAction || clickAction === 'none') {
                console.log("Navigation skipped: no action configured");
                return false;
            }
            
            console.log("Navigating to KPI records:", {kpiType, clickAction, actionDomain});
            
            try {
                const actionConfig = await this.orm.call(
                    "account.dashboard.banner.cell", 
                    "action_view_records_static", 
                    [kpiType, clickAction, actionDomain]
                );
                
                if (!actionConfig || typeof actionConfig !== 'object') {
                    throw new Error("Invalid action configuration received");
                }
                
                if (actionConfig.type) {
                    if (actionConfig.type === 'ir.actions.client' && actionConfig.tag === 'display_notification') {
                        const params = actionConfig.params || {};
                        this.env.services.notification.add(params.message || "Action completed", {
                            type: params.type || "info",
                            title: params.title || "Navigation"
                        });
                    } else {
                        await this.actionService.doAction(actionConfig);
                    }
                } else {
                    this.env.services.notification.add("No navigation action available", {
                        type: "info",
                        title: "Navigation Info"
                    });
                }
            } catch (ormError) {
                throw new Error(`Server communication failed: ${ormError.message || 'Unknown error'}`);
            }
            
            return false; // Prevent default click behavior
            
        } catch (error) {
            console.error("Error navigating to KPI records:", error);
            
            this.env.services.notification.add(error.message || "Error opening records", {
                type: "danger",
                title: "Navigation Error"
            });
            
            return false;
        }
    }
    
    /**
     * Open activity form for KPI follow-up
     * @param {HTMLElement} element - The clicked button element
     */
    async openActivityForm(element) {
        try {
            const kpiLabel = element.dataset.kpiLabel || 'KPI';
            const kpiId = element.dataset.kpiId;
            
            console.log("Opening activity form for KPI:", {kpiLabel, kpiId});
            
            // Create activity form action
            const activityAction = {
                type: 'ir.actions.act_window',
                name: `Follow-up Activity: ${kpiLabel}`,
                res_model: 'mail.activity',
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    'default_summary': `Follow-up on KPI: ${kpiLabel}`,
                    'default_note': `Review and follow-up on ${kpiLabel} metric performance.`,
                    'default_res_model': 'account.dashboard.banner.cell',
                    'default_res_id': parseInt(kpiId) || false,
                    'default_activity_type_id': 1, // Default activity type (usually "To Do")
                }
            };
            
            console.log("Activity form action:", activityAction);
            
            // Execute the action
            await this.actionService.doAction(activityAction);
            
            this.env.services.notification.add(`Activity form opened for ${kpiLabel}`, {
                type: "success",
                title: "Activity Created"
            });
            
            return false; // Prevent event bubbling
            
        } catch (error) {
            console.error("Error opening activity form:", error);
            
            this.env.services.notification.add(error.message || "Error opening activity form", {
                type: "danger",
                title: "Activity Form Error"
            });
            
            return false;
        }
    }
    
    /**
     * Open KPI configuration form
     * @param {HTMLElement} element - The clicked config button element
     */
    async openKpiConfig(element) {
        try {
            // Debug: log all data attributes
            console.log("Config button clicked, all data attributes:", element.dataset);
            
            const kpiId = element.dataset.kpiId || element.getAttribute('data-kpi-id');
            const kpiLabel = element.dataset.kpiLabel || element.getAttribute('data-kpi-label') || 'KPI';
            
            console.log("Opening KPI config for:", {kpiId, kpiLabel});
            console.log("Element:", element);
            console.log("Parent element:", element.closest('.metric-tile-compact, .metric-tile-alert-compact'));
            
            if (!kpiId || kpiId === 'undefined' || kpiId === 'null') {
                // Try to get KPI ID from parent card
                const parentCard = element.closest('.metric-tile-compact, .metric-tile-alert-compact');
                if (parentCard) {
                    const parentKpiId = parentCard.dataset.kpiId || parentCard.getAttribute('data-kpi-id');
                    console.log("Trying parent card KPI ID:", parentKpiId);
                    if (parentKpiId && parentKpiId !== 'undefined' && parentKpiId !== 'null') {
                        const kpiIdNum = parseInt(parentKpiId);
                        if (kpiIdNum && kpiIdNum > 0) {
                            await this._executeKpiConfigAction(kpiIdNum, kpiLabel);
                            return false;
                        }
                    }
                }
                throw new Error(`KPI ID is required but got: '${kpiId}'. Check data attributes.`);
            }
            
            const kpiIdNum = parseInt(kpiId);
            if (!kpiIdNum || kpiIdNum <= 0) {
                throw new Error(`Invalid KPI ID: '${kpiId}'. Must be a positive integer.`);
            }
            
            await this._executeKpiConfigAction(kpiIdNum, kpiLabel);
            return false;
            
        } catch (error) {
            console.error("Error opening KPI config:", error);
            
            this.env.services.notification.add(error.message || "Error opening KPI configuration", {
                type: "danger",
                title: "Configuration Error"
            });
            
            return false;
        }
    }
    
    /**
     * Execute the KPI configuration action
     * @private
     */
    async _executeKpiConfigAction(kpiId, kpiLabel) {
        // Create KPI configuration form action
        const configAction = {
            type: 'ir.actions.act_window',
            name: `Configure KPI: ${kpiLabel}`,
            res_model: 'account.dashboard.banner.cell',
            view_mode: 'form',
            views: [[false, 'form']],
            res_id: kpiId,
            target: 'current', // Open in same window to allow navigation back
        };
        
        console.log("KPI config action:", configAction);
        
        // Execute the action
        await this.actionService.doAction(configAction);
    }
}

export const accountDashboardKanbanBanner = {
    ...kanbanView,
    Renderer: DashboardKanbanRendererBanner,
};

registry.category("views").add("account_dashboard_kanban_banner", accountDashboardKanbanBanner);
