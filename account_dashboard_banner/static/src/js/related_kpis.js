/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";

/**
 * Función global para mostrar KPIs relacionados en la misma vista
 * @param {HTMLElement} button - El botón que fue clickeado
 */
window.viewRelatedKpis = async function(button) {
    try {
        // Prevenir propagación del evento
        event.preventDefault();
        event.stopPropagation();

        const kpiId = parseInt(button.getAttribute('data-kpi-id'));
        const kpiLabel = button.getAttribute('data-kpi-label');
        
        if (!kpiId) {
            console.error('No KPI ID found');
            return false;
        }

        // Obtener datos de KPIs relacionados desde el backend
        try {
            // Usar fetch API como fallback más compatible
            const response = await fetch('/web/dataset/call_kw', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        model: 'account.dashboard.banner.cell',
                        method: 'get_related_kpi_ids',
                        args: [kpiId],
                        kwargs: {}
                    }
                })
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error.message || 'Unknown error');
            }

            const relatedKpiIds = data.result || [];
            
            // Mostrar solo los KPIs relacionados + el KPI principal
            showRelatedKpisOnly([kpiId, ...relatedKpiIds], kpiLabel);

        } catch (error) {
            console.error('Error fetching related KPIs:', error);
            // Fallback: mostrar mensaje de error
            showKpiMessage(`Error loading related KPIs for "${kpiLabel}"`);
        }

        return false;
    } catch (error) {
        console.error('Error in viewRelatedKpis:', error);
        return false;
    }
};

/**
 * Mostrar solo los KPIs relacionados en el dashboard
 * @param {Array} kpiIds - IDs de los KPIs a mostrar
 * @param {String} mainKpiLabel - Label del KPI principal
 */
function showRelatedKpisOnly(kpiIds, mainKpiLabel) {
    const dashboard = document.getElementById('dashboard_banner');
    if (!dashboard) return;

    const allKpiTiles = dashboard.querySelectorAll('.metric-tile-compact');
    let visibleCount = 0;
    let hiddenCount = 0;

    // Ocultar todos los KPIs que no están relacionados
    allKpiTiles.forEach(tile => {
        const tileKpiId = parseInt(tile.getAttribute('data-kpi-id'));
        
        if (kpiIds.includes(tileKpiId)) {
            // Mostrar KPI relacionado con efecto de resaltado
            tile.style.display = 'block';
            tile.classList.add('kpi-related-highlight');
            
            // Resaltar el KPI principal de forma especial
            if (tileKpiId === kpiIds[0]) {
                tile.classList.add('kpi-main-highlight');
            }
            
            visibleCount++;
        } else {
            // Ocultar KPIs no relacionados
            tile.style.display = 'none';
            tile.classList.remove('kpi-related-highlight', 'kpi-main-highlight');
            hiddenCount++;
        }
    });

    // Mostrar mensaje informativo
    showRelatedKpisHeader(mainKpiLabel, visibleCount, hiddenCount);
    
    // Actualizar filtros de categoría
    updateCategoryFilters(false);
}

/**
 * Mostrar encabezado con información de KPIs relacionados
 * @param {String} mainKpiLabel - Label del KPI principal
 * @param {Number} visibleCount - Cantidad de KPIs visibles
 * @param {Number} hiddenCount - Cantidad de KPIs ocultos
 */
function showRelatedKpisHeader(mainKpiLabel, visibleCount, hiddenCount) {
    const dashboard = document.getElementById('dashboard_banner');
    if (!dashboard) return;

    // Remover encabezado anterior si existe
    const existingHeader = document.getElementById('related-kpis-header');
    if (existingHeader) {
        existingHeader.remove();
    }

    // Crear nuevo encabezado
    const header = document.createElement('div');
    header.id = 'related-kpis-header';
    header.className = 'alert alert-info related-kpis-header';
    header.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
            <div>
                <i class="fa fa-sitemap me-2"></i>
                <strong>Related KPIs for "${mainKpiLabel}"</strong> 
                <span class="badge bg-primary ms-2">${visibleCount} KPIs shown</span>
                <span class="text-muted ms-1">(${hiddenCount} KPIs hidden)</span>
            </div>
            <div>
                <button class="btn btn-sm btn-outline-secondary me-2" onclick="showAllKpis()">
                    <i class="fa fa-eye me-1"></i>Show All KPIs
                </button>
                <button class="btn btn-sm btn-secondary" onclick="clearRelatedKpisView()">
                    <i class="fa fa-times me-1"></i>Clear Filter
                </button>
            </div>
        </div>
    `;

    // Insertar encabezado después de los filtros de categoría
    const categoryFilters = dashboard.querySelector('.category-filters');
    if (categoryFilters) {
        categoryFilters.parentNode.insertBefore(header, categoryFilters.nextSibling);
    }
}

/**
 * Limpiar la vista de KPIs relacionados y mostrar todos
 */
window.clearRelatedKpisView = function() {
    const dashboard = document.getElementById('dashboard_banner');
    if (!dashboard) return;

    // Mostrar todos los KPIs
    const allKpiTiles = dashboard.querySelectorAll('.metric-tile-compact');
    allKpiTiles.forEach(tile => {
        tile.style.display = 'block';
        tile.classList.remove('kpi-related-highlight', 'kpi-main-highlight');
    });

    // Remover encabezado
    const header = document.getElementById('related-kpis-header');
    if (header) {
        header.remove();
    }

    // Restaurar filtros de categoría
    updateCategoryFilters(true);
    
    // Activar filtro "All"
    const allButton = document.querySelector('[data-category="all"]');
    if (allButton) {
        filterKpisByCategory('all');
    }
};

/**
 * Mostrar todos los KPIs (alias para clearRelatedKpisView)
 */
window.showAllKpis = window.clearRelatedKpisView;

/**
 * Actualizar estado de filtros de categoría
 * @param {Boolean} enable - Si activar o desactivar los filtros
 */
function updateCategoryFilters(enable) {
    const filterButtons = document.querySelectorAll('.filter-buttons .btn');
    filterButtons.forEach(btn => {
        if (enable) {
            btn.disabled = false;
            btn.style.opacity = '1';
        } else {
            btn.disabled = true;
            btn.style.opacity = '0.5';
        }
    });
}

/**
 * Mostrar mensaje informativo
 * @param {String} message - Mensaje a mostrar
 */
function showKpiMessage(message) {
    const dashboard = document.getElementById('dashboard_banner');
    if (!dashboard) return;

    // Remover mensaje anterior
    const existingMsg = document.getElementById('kpi-message');
    if (existingMsg) {
        existingMsg.remove();
    }

    // Crear nuevo mensaje
    const msgDiv = document.createElement('div');
    msgDiv.id = 'kpi-message';
    msgDiv.className = 'alert alert-warning';
    msgDiv.innerHTML = `
        <i class="fa fa-exclamation-triangle me-2"></i>
        ${message}
        <button class="btn btn-sm btn-secondary ms-3" onclick="clearRelatedKpisView()">
            <i class="fa fa-refresh me-1"></i>Reset View
        </button>
    `;

    // Insertar mensaje
    const categoryFilters = dashboard.querySelector('.category-filters');
    if (categoryFilters) {
        categoryFilters.parentNode.insertBefore(msgDiv, categoryFilters.nextSibling);
    }
}