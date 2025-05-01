/**
 * Main JavaScript for Banking App Analyzer
 * Modern Dashboard Version
 */

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {

    // Initialize sidebar functionality
    initSidebar();

    // Initialize theme switcher
    initThemeSwitcher();

    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Format large numbers for better readability
    window.formatNumber = function(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num;
    };

    // Common functions for dealing with sentiment analysis
    window.getSentimentColor = function(sentiment) {
        if (sentiment === 'positive' || sentiment > 0.1) {
            return 'rgba(76, 201, 240, 0.8)'; // Updated color for modern theme
        } else if (sentiment === 'negative' || sentiment < -0.1) {
            return 'rgba(247, 37, 133, 0.8)'; // Updated color for modern theme
        } else {
            return 'rgba(58, 12, 163, 0.8)'; // Updated color for modern theme
        }
    };

    window.getSentimentBorderColor = function(sentiment) {
        if (sentiment === 'positive' || sentiment > 0.1) {
            return 'rgba(76, 201, 240, 1)'; // Updated color for modern theme
        } else if (sentiment === 'negative' || sentiment < -0.1) {
            return 'rgba(247, 37, 133, 1)'; // Updated color for modern theme
        } else {
            return 'rgba(58, 12, 163, 1)'; // Updated color for modern theme
        }
    };

    // Format date for better display
    window.formatDate = function(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString();
    };

    // Calculate time ago from date
    window.timeAgo = function(dateString) {
        const date = new Date(dateString);
        const seconds = Math.floor((new Date() - date) / 1000);

        let interval = Math.floor(seconds / 31536000);
        if (interval >= 1) {
            return interval + ' year' + (interval === 1 ? '' : 's') + ' ago';
        }

        interval = Math.floor(seconds / 2592000);
        if (interval >= 1) {
            return interval + ' month' + (interval === 1 ? '' : 's') + ' ago';
        }

        interval = Math.floor(seconds / 86400);
        if (interval >= 1) {
            return interval + ' day' + (interval === 1 ? '' : 's') + ' ago';
        }

        interval = Math.floor(seconds / 3600);
        if (interval >= 1) {
            return interval + ' hour' + (interval === 1 ? '' : 's') + ' ago';
        }

        interval = Math.floor(seconds / 60);
        if (interval >= 1) {
            return interval + ' minute' + (interval === 1 ? '' : 's') + ' ago';
        }

        return Math.floor(seconds) + ' second' + (seconds === 1 ? '' : 's') + ' ago';
    };

    // Toast notification system
    window.showToast = function(title, message, type = 'info') {
        // Create toast container if it doesn't exist
        if (!document.getElementById('toastContainer')) {
            console.warn('Toast container not found, creating one');
            const toastContainer = document.createElement('div');
            toastContainer.id = 'toastContainer';
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }

        // Set icon and background color based on type
        let icon, bgClass;
        switch(type) {
            case 'success':
                icon = 'fa-check-circle';
                bgClass = 'bg-success';
                break;
            case 'error':
            case 'danger':
                icon = 'fa-exclamation-circle';
                bgClass = 'bg-danger';
                break;
            case 'warning':
                icon = 'fa-exclamation-triangle';
                bgClass = 'bg-warning';
                break;
            case 'info':
            default:
                icon = 'fa-info-circle';
                bgClass = 'bg-primary';
                break;
        }

        // Create toast element
        const toastId = 'toast-' + Date.now();
        const toastHtml = `
            <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="toast-header ${bgClass} text-white">
                    <i class="fas ${icon} me-2"></i>
                    <strong class="me-auto">${title}</strong>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;

        document.getElementById('toastContainer').insertAdjacentHTML('beforeend', toastHtml);

        // Initialize and show the toast
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement, {
            delay: 5000 // Auto-hide after 5 seconds
        });
        toast.show();

        // Remove toast after it's hidden
        toastElement.addEventListener('hidden.bs.toast', function() {
            toastElement.remove();
        });

        return toast;
    };

    // Alias for error toast
    window.showError = function(message) {
        return window.showToast('Error', message, 'error');
    };

    // Success toast
    window.showSuccess = function(message) {
        return window.showToast('Success', message, 'success');
    };

    // Warning toast
    window.showWarning = function(message) {
        return window.showToast('Warning', message, 'warning');
    };

    // Info toast
    window.showInfo = function(message) {
        return window.showToast('Information', message, 'info');
    };

    // Initialize DataTables with common settings
    window.initDataTable = function(tableId, options = {}) {
        // Default options
        const defaultOptions = {
            responsive: true,
            lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]],
            pageLength: 25,
            dom: 'Bfrtip',
            buttons: [
                {
                    extend: 'copy',
                    className: 'btn btn-sm btn-outline-primary'
                },
                {
                    extend: 'csv',
                    className: 'btn btn-sm btn-outline-primary'
                },
                {
                    extend: 'excel',
                    className: 'btn btn-sm btn-outline-primary'
                },
                {
                    extend: 'pdf',
                    className: 'btn btn-sm btn-outline-primary'
                },
                {
                    extend: 'print',
                    className: 'btn btn-sm btn-outline-primary'
                },
                {
                    extend: 'colvis',
                    className: 'btn btn-sm btn-outline-primary'
                }
            ],
            language: {
                search: "_INPUT_",
                searchPlaceholder: "Search...",
                lengthMenu: "Show _MENU_ entries",
                info: "Showing _START_ to _END_ of _TOTAL_ entries",
                infoEmpty: "Showing 0 to 0 of 0 entries",
                infoFiltered: "(filtered from _MAX_ total entries)",
                paginate: {
                    first: '<i class="fas fa-angle-double-left"></i>',
                    previous: '<i class="fas fa-angle-left"></i>',
                    next: '<i class="fas fa-angle-right"></i>',
                    last: '<i class="fas fa-angle-double-right"></i>'
                }
            }
        };

        // Merge default options with provided options
        const mergedOptions = {...defaultOptions, ...options};

        // Initialize DataTable
        return new DataTable('#' + tableId, mergedOptions);
    };
});

// Initialize sidebar functionality
function initSidebar() {
    const sidebar = document.getElementById('sidebar');
    const sidebarCollapseBtn = document.getElementById('sidebarCollapseBtn');
    const sidebarCollapse = document.getElementById('sidebarCollapse');
    const content = document.getElementById('content');

    // Toggle sidebar on button click (desktop)
    if (sidebarCollapseBtn) {
        sidebarCollapseBtn.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');

            // Store sidebar state in localStorage
            localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
        });
    }

    // Toggle sidebar on button click (mobile)
    if (sidebarCollapse) {
        sidebarCollapse.addEventListener('click', function() {
            sidebar.classList.toggle('active');

            // Add overlay when sidebar is active on mobile
            if (sidebar.classList.contains('active')) {
                const overlay = document.createElement('div');
                overlay.className = 'sidebar-overlay';
                overlay.id = 'sidebarOverlay';
                document.body.appendChild(overlay);

                // Close sidebar when clicking on overlay
                overlay.addEventListener('click', function() {
                    sidebar.classList.remove('active');
                    overlay.remove();
                });
            } else {
                const overlay = document.getElementById('sidebarOverlay');
                if (overlay) {
                    overlay.remove();
                }
            }
        });
    }

    // Check if sidebar state is stored in localStorage
    if (localStorage.getItem('sidebarCollapsed') === 'true') {
        sidebar.classList.add('collapsed');
    }

    // Handle submenu toggles
    const submenuToggles = document.querySelectorAll('.nav-link[data-bs-toggle="collapse"]');
    submenuToggles.forEach(function(toggle) {
        toggle.addEventListener('click', function(e) {
            if (sidebar.classList.contains('collapsed')) {
                e.preventDefault();
                e.stopPropagation();

                // Expand sidebar when clicking on a collapsed menu item with submenu
                sidebar.classList.remove('collapsed');
                localStorage.setItem('sidebarCollapsed', 'false');

                // Open the submenu after a short delay
                setTimeout(() => {
                    const targetId = this.getAttribute('href');
                    const targetCollapse = document.querySelector(targetId);
                    const bsCollapse = new bootstrap.Collapse(targetCollapse);
                    bsCollapse.show();
                }, 300);
            }
        });
    });
}

// Initialize theme switcher
function initThemeSwitcher() {
    const themeSwitch = document.getElementById('themeSwitch');

    if (!themeSwitch) return;

    // Check if theme preference is stored in localStorage
    const currentTheme = localStorage.getItem('theme') || 'light';

    // Set initial theme
    document.documentElement.setAttribute('data-bs-theme', currentTheme);

    // Set switch state based on current theme
    themeSwitch.checked = currentTheme === 'dark';

    // Listen for switch changes
    themeSwitch.addEventListener('change', function() {
        if (this.checked) {
            document.documentElement.setAttribute('data-bs-theme', 'dark');
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.setAttribute('data-bs-theme', 'light');
            localStorage.setItem('theme', 'light');
        }
    });
}
