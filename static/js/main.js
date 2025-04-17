/**
 * Main JavaScript for Banking App Analyzer
 */

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    
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
            return 'rgba(40, 167, 69, 0.8)';
        } else if (sentiment === 'negative' || sentiment < -0.1) {
            return 'rgba(220, 53, 69, 0.8)';
        } else {
            return 'rgba(255, 193, 7, 0.8)';
        }
    };
    
    window.getSentimentBorderColor = function(sentiment) {
        if (sentiment === 'positive' || sentiment > 0.1) {
            return 'rgba(40, 167, 69, 1)';
        } else if (sentiment === 'negative' || sentiment < -0.1) {
            return 'rgba(220, 53, 69, 1)';
        } else {
            return 'rgba(255, 193, 7, 1)';
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
    
    // Handle error display with toast notifications
    window.showError = function(message) {
        // Create toast container if it doesn't exist
        if (!document.getElementById('toast-container')) {
            const toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            document.body.appendChild(toastContainer);
        }
        
        // Create toast element
        const toastId = 'toast-' + Date.now();
        const toastHtml = `
            <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="toast-header bg-danger text-white">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    <strong class="me-auto">Error</strong>
                    <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;
        
        document.getElementById('toast-container').insertAdjacentHTML('beforeend', toastHtml);
        
        // Initialize and show the toast
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement);
        toast.show();
        
        // Remove toast after it's hidden
        toastElement.addEventListener('hidden.bs.toast', function() {
            toastElement.remove();
        });
    };
});
