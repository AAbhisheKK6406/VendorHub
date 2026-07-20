/**
 * ==========================================================================
 * VendorHub - Enterprise SaaS Dashboard Core Script
 * Project Name: VendorHub
 * Framework: Vanilla JavaScript (ES6+) - Strict Architecture
 * ==========================================================================
 */

"use strict";

document.addEventListener("DOMContentLoaded", () => {
    VendorHubDashboard.init();
});

const VendorHubDashboard = (() => {
    // Cached DOM Elements to prevent repeated queries
    const DOM = {};

    /**
     * 1. Initialization Orchestrator
     */
    const init = () => {
        try {
            cacheElements();
            showLoadingState(true);

            // Execute modular features safely
            initFlashMessages();
            initStatisticsAnimations();
            initQuickActions();
            initTableEnhancements();

            showLoadingState(false);
        } catch (error) {
            console.error("[VendorHub Error] Critical initialization failure:", error);
            // Ensure loading screen hides even if an internal script fails
            showLoadingState(false);
        }
    };

    /**
     * 2. Cache DOM Elements & Setup Selectors
     */
    const cacheElements = () => {
        DOM.body = document.body;
        DOM.flashMessages = document.querySelectorAll("#flash-messages-container .alert");
        DOM.tables = document.querySelectorAll(".table");
        
        // Quick Action Targets
        DOM.actionButtons = document.querySelectorAll("#quick-actions-bar .btn");

        // Numeric KPI Animation Targets
        DOM.kpis = [
            { el: document.querySelector("#card-total-products h2"), isCurrency: false },
            { el: document.querySelector("#card-low-stock h2"), isCurrency: false },
            { el: document.querySelector("#card-total-customers h2"), isCurrency: false },
            { el: document.querySelector("#card-total-bills h2"), isCurrency: false },
            { el: document.querySelector("#card-today-sales h2"), isCurrency: true },
            { el: document.querySelector("#card-monthly-revenue h2"), isCurrency: true }
        ].filter(kpi => kpi.el !== null); // Strip missing DOM elements to prevent null reference breaks
    };

    /**
     * 3. Statistics Card Animation
     */
    const initStatisticsAnimations = () => {
        DOM.kpis.forEach(kpi => {
            const rawValue = kpi.el.textContent.trim();
            // Strip currencies ($ or ₹) and comma formatting separators for raw calculation
            const targetValue = parseFloat(rawValue.replace(/[^0-9.-]+/g, ""));

            if (isNaN(targetValue) || targetValue <= 0) return;

            animateNumber(kpi.el, 0, targetValue, 1000, kpi.isCurrency);
        });
    };

    const animateNumber = (element, start, end, duration, isCurrency) => {
        const startTime = performance.now();

        const updateNumber = (currentTime) => {
            const elapsedTime = currentTime - startTime;
            const progress = Math.min(elapsedTime / duration, 1);
            
            // Out-Quad easing for a clean, professional slow-down finish
            const easeProgress = progress * (2 - progress);
            const currentValue = start + (end - start) * easeProgress;

            if (isCurrency) {
                // Formats to user locale format with standard two decimal rounding
                element.textContent = new Intl.NumberFormat(navigator.language || 'en-IN', {
                    style: 'currency',
                    currency: 'INR' // Adaptable fallback based on dashboard layout standard
                }).format(currentValue);
            } else {
                element.textContent = Math.floor(currentValue).toLocaleString();
            }

            if (progress < 1) {
                requestAnimationFrame(updateNumber);
            }
        };

        requestAnimationFrame(updateNumber);
    };

    /**
     * 4. Quick Action Buttons Handling
     */
    const initQuickActions = () => {
        DOM.actionButtons.forEach(button => {
            button.addEventListener("click", (e) => {
                if (button.disabled || button.classList.contains("is-processing")) {
                    e.preventDefault();
                    return;
                }

                // Debounce prevention strategy against accidental double-submissions
                button.classList.add("is-processing");
                button.setAttribute("aria-busy", "true");
                
                const originalText = button.innerHTML;
                button.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> Processing...`;

                // Gracefully timeout processing after safety window if page doesn't shift redirect
                setTimeout(() => {
                    button.classList.remove("is-processing");
                    button.removeAttribute("aria-busy");
                    button.innerHTML = originalText;
                }, 4000);
            });
        });
    };

    /**
     * 5. Flash Message Handling
     */
    const initFlashMessages = () => {
        DOM.flashMessages.forEach(alert => {
            // Initiate automatic close counter after a clean 4-second visibility delay
            setTimeout(() => {
                dismissAlertGracefully(alert);
            }, 4000);
        });
    };

    const dismissAlertGracefully = (alertElement) => {
        alertElement.style.transition = "opacity 0.5s cubic-bezier(0.4, 0, 0.2, 1), transform 0.5s ease";
        alertElement.style.opacity = "0";
        alertElement.style.transform = "translateY(-10px)";

        alertElement.addEventListener("transitionend", function handleRemoval(e) {
            if (e.propertyName === "opacity") {
                alertElement.remove();
                alertElement.removeEventListener("transitionend", handleRemoval);
            }
        });
    };

    /**
     * 6. Table Enhancements & Empty State Detection
     */
    const initTableEnhancements = () => {
        DOM.tables.forEach(table => {
            const tbody = table.querySelector("tbody");
            // Check for raw row counts discounting manual whitespace containers
            const rows = tbody ? tbody.querySelectorAll("tr:not(.empty-state-row)") : [];

            if (rows.length === 0 && tbody) {
                renderEmptyState(table, tbody);
            } else {
                setupKeyboardNavigation(rows);
            }
        });
    };

    const renderEmptyState = (table, tbody) => {
        const columnCount = table.querySelectorAll("thead th").length || 4;
        const emptyRow = document.createElement("tr");
        emptyRow.className = "empty-state-row";
        
        emptyRow.innerHTML = `
            <td colspan="${columnCount}" class="text-center py-5 text-muted">
                <div class="d-flex flex-column align-items-center justify-content-center">
                    <i class="bi bi-inbox fs-2 mb-2 text-secondary"></i>
                    <p class="mb-0 fw-medium">No records found matching this workspace</p>
                    <small class="text-xs text-secondary">New entries will populate automatically once synced.</small>
                </div>
            </td>
        `;
        tbody.appendChild(emptyRow);
    };

    const setupKeyboardNavigation = (rows) => {
        rows.forEach(row => {
            row.setAttribute("tabindex", "0"); // Allows focus tracking across core table assets
            
            row.addEventListener("keydown", (e) => {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    row.click(); // Trigger routing or click handlers bound to table rows safely
                }
            });
        });
    };

    /**
     * 7. Loading State Overlay Utilities
     */
    const showLoadingState = (isLoading) => {
        let loader = document.getElementById("dashboard-global-loader");
        
        if (isLoading) {
            if (!loader) {
                loader = document.createElement("div");
                loader.id = "dashboard-global-loader";
                // Style attributes handled out of layout scope for complete blocking isolation
                Object.assign(loader.style, {
                    position: "fixed",
                    top: "0",
                    left: "0",
                    width: "100vw",
                    height: "100vh",
                    backgroundColor: "rgba(247, 248, 249, 0.85)",
                    zIndex: "9999",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    transition: "opacity 0.25s ease-out"
                });
                loader.innerHTML = `
                    <div class="text-center">
                        <div class="spinner-border text-primary mb-2" role="status" style="width: 2.5rem; height: 2.5rem; --bs-spinner-border-width: 0.2em;"></div>
                        <p class="text-muted small fw-medium mb-0">Synchronizing VendorHub...</p>
                    </div>
                `;
                DOM.body.appendChild(loader);
            }
        } else if (loader) {
            loader.style.opacity = "0";
            setTimeout(() => loader.remove(), 250);
        }
    };

    return { init };
})();