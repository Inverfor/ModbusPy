/**
 * Modbus Industrial Server - Web Application JavaScript
 * Optimized for Raspberry Pi Zero 2W
 */

// Global application state
const ModbusApp = {
    config: {
        updateInterval: 5000,
        chartUpdateInterval: 30000,
        maxDataPoints: 50,
        apiTimeout: 10000
    },
    state: {
        serverRunning: false,
        currentPage: 'dashboard',
        selectedSlave: null,
        charts: {},
        intervals: {}
    }
};

// Utility functions
const Utils = {
    /**
     * Format bytes to human readable format
     */
    formatBytes: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    /**
     * Format numbers with locale-specific formatting
     */
    formatNumber: function(num) {
        return new Intl.NumberFormat('es-ES').format(num);
    },

    /**
     * Format timestamp to local string
     */
    formatTimestamp: function(timestamp) {
        return new Date(timestamp).toLocaleString('es-ES', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    },

    /**
     * Debounce function calls
     */
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * Throttle function calls
     */
    throttle: function(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    /**
     * Safe API call with timeout and error handling
     */
    apiCall: function(url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), ModbusApp.config.apiTimeout);

        return fetch(url, {
            ...options,
            signal: controller.signal
        })
        .then(response => {
            clearTimeout(timeoutId);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .catch(error => {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error('Request timeout');
            }
            throw error;
        });
    }
};

// Alert system
const AlertSystem = {
    /**
     * Show alert message
     */
    show: function(message, type = 'info', duration = 5000) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        
        const iconMap = {
            'success': 'fa-check-circle',
            'danger': 'fa-exclamation-triangle',
            'warning': 'fa-exclamation-triangle',
            'info': 'fa-info-circle'
        };
        
        alertDiv.innerHTML = `
            <i class="fas ${iconMap[type] || 'fa-info-circle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        // Auto-dismiss
        if (duration > 0) {
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, duration);
        }
        
        return alertDiv;
    },

    /**
     * Show success message
     */
    success: function(message, duration = 3000) {
        return this.show(message, 'success', duration);
    },

    /**
     * Show error message
     */
    error: function(message, duration = 8000) {
        return this.show(message, 'danger', duration);
    },

    /**
     * Show warning message
     */
    warning: function(message, duration = 5000) {
        return this.show(message, 'warning', duration);
    },

    /**
     * Show info message
     */
    info: function(message, duration = 4000) {
        return this.show(message, 'info', duration);
    }
};

// Performance monitor for Pi Zero 2W
const PerformanceMonitor = {
    metrics: {
        apiCalls: 0,
        apiErrors: 0,
        memoryUsage: 0,
        renderTime: 0
    },

    /**
     * Start monitoring
     */
    start: function() {
        // Monitor memory usage (if available)
        if (performance.memory) {
            this.metrics.memoryUsage = performance.memory.usedJSHeapSize;
        }

        // Monitor API performance
        this.startApiMonitoring();
    },

    /**
     * Monitor API calls
     */
    startApiMonitoring: function() {
        const originalFetch = window.fetch;
        const self = this;
        
        window.fetch = function(...args) {
            self.metrics.apiCalls++;
            const startTime = performance.now();
            
            return originalFetch.apply(this, args)
                .then(response => {
                    const endTime = performance.now();
                    const duration = endTime - startTime;
                    
                    if (!response.ok) {
                        self.metrics.apiErrors++;
                    }
                    
                    // Log slow requests (>2s on Pi Zero 2W)
                    if (duration > 2000) {
                        console.warn(`Slow API call: ${args[0]} took ${duration.toFixed(2)}ms`);
                    }
                    
                    return response;
                })
                .catch(error => {
                    self.metrics.apiErrors++;
                    throw error;
                });
        };
    },

    /**
     * Get performance metrics
     */
    getMetrics: function() {
        if (performance.memory) {
            this.metrics.memoryUsage = performance.memory.usedJSHeapSize;
        }
        
        return { ...this.metrics };
    },

    /**
     * Check if performance is degraded
     */
    isPerformanceDegraded: function() {
        const errorRate = this.metrics.apiErrors / Math.max(this.metrics.apiCalls, 1);
        return errorRate > 0.1 || (performance.memory && performance.memory.usedJSHeapSize > 50 * 1024 * 1024);
    }
};

// Chart management optimized for Pi Zero 2W
const ChartManager = {
    charts: {},
    defaultOptions: {
        responsive: true,
        maintainAspectRatio: false,
        animation: {
            duration: 0 // Disable animations for better performance
        },
        elements: {
            point: {
                radius: 2 // Smaller points for better performance
            }
        },
        plugins: {
            legend: {
                display: true,
                position: 'top'
            }
        }
    },

    /**
     * Create optimized chart
     */
    create: function(canvasId, config) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) {
            console.error(`Canvas with id '${canvasId}' not found`);
            return null;
        }

        // Merge with default options
        const mergedConfig = {
            ...config,
            options: {
                ...this.defaultOptions,
                ...config.options
            }
        };

        const chart = new Chart(canvas, mergedConfig);
        this.charts[canvasId] = chart;
        return chart;
    },

    /**
     * Update chart data efficiently
     */
    updateData: function(chartId, newData) {
        const chart = this.charts[chartId];
        if (!chart) return;

        // Limit data points for performance
        if (newData.labels && newData.labels.length > ModbusApp.config.maxDataPoints) {
            newData.labels = newData.labels.slice(-ModbusApp.config.maxDataPoints);
            newData.datasets.forEach(dataset => {
                if (dataset.data) {
                    dataset.data = dataset.data.slice(-ModbusApp.config.maxDataPoints);
                }
            });
        }

        chart.data = newData;
        chart.update('none'); // No animation for better performance
    },

    /**
     * Destroy chart
     */
    destroy: function(chartId) {
        const chart = this.charts[chartId];
        if (chart) {
            chart.destroy();
            delete this.charts[chartId];
        }
    },

    /**
     * Destroy all charts
     */
    destroyAll: function() {
        Object.keys(this.charts).forEach(chartId => {
            this.destroy(chartId);
        });
    }
};

// Data cache for reducing API calls
const DataCache = {
    cache: new Map(),
    maxAge: 30000, // 30 seconds

    /**
     * Get cached data
     */
    get: function(key) {
        const item = this.cache.get(key);
        if (!item) return null;

        if (Date.now() - item.timestamp > this.maxAge) {
            this.cache.delete(key);
            return null;
        }

        return item.data;
    },

    /**
     * Set cached data
     */
    set: function(key, data) {
        this.cache.set(key, {
            data: data,
            timestamp: Date.now()
        });

        // Cleanup old entries
        if (this.cache.size > 50) {
            const oldestKey = this.cache.keys().next().value;
            this.cache.delete(oldestKey);
        }
    },

    /**
     * Clear cache
     */
    clear: function() {
        this.cache.clear();
    }
};

// Connection manager
const ConnectionManager = {
    isOnline: navigator.onLine,
    reconnectAttempts: 0,
    maxReconnectAttempts: 5,

    /**
     * Initialize connection monitoring
     */
    init: function() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.reconnectAttempts = 0;
            AlertSystem.success('Conexión restaurada');
            this.onReconnect();
        });

        window.addEventListener('offline', () => {
            this.isOnline = false;
            AlertSystem.warning('Conexión perdida. Reintentando...', 0);
        });

        // Periodic connection check
        setInterval(() => {
            this.checkConnection();
        }, 10000);
    },

    /**
     * Check connection status
     */
    checkConnection: function() {
        if (!this.isOnline) return;

        Utils.apiCall('/api/system/status')
            .then(() => {
                this.reconnectAttempts = 0;
            })
            .catch(() => {
                this.handleConnectionError();
            });
    },

    /**
     * Handle connection errors
     */
    handleConnectionError: function() {
        this.reconnectAttempts++;
        
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            AlertSystem.error('No se puede conectar al servidor. Verifique la conexión.', 0);
        }
    },

    /**
     * Handle reconnection
     */
    onReconnect: function() {
        // Refresh current page data
        if (typeof window.refreshCurrentPage === 'function') {
            window.refreshCurrentPage();
        }
    }
};

// Page-specific functionality
const PageManager = {
    currentPage: null,
    
    /**
     * Initialize page
     */
    init: function() {
        this.currentPage = this.getCurrentPage();
        this.setupPageSpecificFeatures();
    },

    /**
     * Get current page from URL
     */
    getCurrentPage: function() {
        const path = window.location.pathname;
        if (path.includes('slaves')) return 'slaves';
        if (path.includes('charts')) return 'charts';
        if (path.includes('config')) return 'config';
        return 'dashboard';
    },

    /**
     * Setup page-specific features
     */
    setupPageSpecificFeatures: function() {
        switch (this.currentPage) {
            case 'dashboard':
                this.setupDashboard();
                break;
            case 'slaves':
                this.setupSlaves();
                break;
            case 'charts':
                this.setupCharts();
                break;
            case 'config':
                this.setupConfig();
                break;
        }
    },

    /**
     * Setup dashboard features
     */
    setupDashboard: function() {
        // Dashboard-specific initialization
        console.log('Dashboard initialized');
    },

    /**
     * Setup slaves page features
     */
    setupSlaves: function() {
        // Slaves page-specific initialization
        console.log('Slaves page initialized');
    },

    /**
     * Setup charts page features
     */
    setupCharts: function() {
        // Charts page-specific initialization
        console.log('Charts page initialized');
    },

    /**
     * Setup config page features
     */
    setupConfig: function() {
        // Config page-specific initialization
        console.log('Config page initialized');
    }
};

// Keyboard shortcuts
const KeyboardShortcuts = {
    shortcuts: {
        'ctrl+r': () => window.location.reload(),
        'ctrl+h': () => window.location.href = '/',
        'ctrl+s': () => window.location.href = '/slaves',
        'ctrl+g': () => window.location.href = '/charts',
        'ctrl+c': () => window.location.href = '/config'
    },

    /**
     * Initialize keyboard shortcuts
     */
    init: function() {
        document.addEventListener('keydown', (e) => {
            const key = this.getKeyString(e);
            const shortcut = this.shortcuts[key];
            
            if (shortcut) {
                e.preventDefault();
                shortcut();
            }
        });
    },

    /**
     * Get key string from event
     */
    getKeyString: function(e) {
        const parts = [];
        if (e.ctrlKey) parts.push('ctrl');
        if (e.altKey) parts.push('alt');
        if (e.shiftKey) parts.push('shift');
        parts.push(e.key.toLowerCase());
        return parts.join('+');
    }
};

// Mobile optimization
const MobileOptimizer = {
    isMobile: /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent),
    
    /**
     * Initialize mobile optimizations
     */
    init: function() {
        if (this.isMobile) {
            this.optimizeForMobile();
        }
    },

    /**
     * Apply mobile optimizations
     */
    optimizeForMobile: function() {
        // Reduce update frequency on mobile
        ModbusApp.config.updateInterval = 10000;
        ModbusApp.config.chartUpdateInterval = 60000;
        
        // Add mobile-specific CSS class
        document.body.classList.add('mobile-device');
        
        // Optimize touch interactions
        this.optimizeTouchInteractions();
    },

    /**
     * Optimize touch interactions
     */
    optimizeTouchInteractions: function() {
        // Add touch-friendly button sizes
        const style = document.createElement('style');
        style.textContent = `
            .mobile-device .btn {
                min-height: 44px;
                min-width: 44px;
            }
            .mobile-device .table td {
                padding: 12px 8px;
            }
        `;
        document.head.appendChild(style);
    }
};

// Application initialization
const App = {
    /**
     * Initialize the application
     */
    init: function() {
        console.log('Initializing Modbus Industrial Server Web App...');
        
        // Initialize core systems
        PerformanceMonitor.start();
        ConnectionManager.init();
        PageManager.init();
        KeyboardShortcuts.init();
        MobileOptimizer.init();
        
        // Setup global error handling
        this.setupErrorHandling();
        
        // Setup periodic cleanup
        this.setupCleanup();
        
        console.log('App initialized successfully');
    },

    /**
     * Setup global error handling
     */
    setupErrorHandling: function() {
        window.addEventListener('error', (e) => {
            console.error('Global error:', e.error);
            AlertSystem.error('Se produjo un error inesperado');
        });

        window.addEventListener('unhandledrejection', (e) => {
            console.error('Unhandled promise rejection:', e.reason);
            AlertSystem.error('Error de conexión con el servidor');
        });
    },

    /**
     * Setup periodic cleanup
     */
    setupCleanup: function() {
        // Cleanup every 5 minutes
        setInterval(() => {
            DataCache.clear();
            
            // Force garbage collection if available
            if (window.gc) {
                window.gc();
            }
        }, 300000);
    }
};

// Global functions for backward compatibility
window.showAlert = AlertSystem.show;
window.formatBytes = Utils.formatBytes;
window.formatNumber = Utils.formatNumber;

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => App.init());
} else {
    App.init();
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        ModbusApp,
        Utils,
        AlertSystem,
        PerformanceMonitor,
        ChartManager,
        DataCache,
        ConnectionManager
    };
}
