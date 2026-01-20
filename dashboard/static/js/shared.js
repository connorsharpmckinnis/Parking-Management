/**
 * Parking Management Dashboard - Shared JavaScript
 * Town of Apex | v0.8.1
 */

const APP_VERSION = '0.8.1';
const CONTROL_PLANE_URL = '/api'; // Proxied through our server

// ============================================
// Utility Functions
// ============================================

/**
 * Format UTC timestamp to EST/New York timezone
 */
function formatTimestamp(isoString) {
    if (!isoString) return 'Never';
    try {
        const date = new Date(isoString);
        return date.toLocaleString('en-US', {
            timeZone: 'America/New_York',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    } catch (e) {
        return isoString;
    }
}

/**
 * Make API requests with error handling
 */
async function apiRequest(endpoint, options = {}) {
    try {
        const response = await fetch(`${CONTROL_PLANE_URL}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText || `HTTP ${response.status}`);
        }

        if (response.status === 204) return null;
        return await response.json();
    } catch (error) {
        console.error(`API Error (${endpoint}):`, error);
        throw error;
    }
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container') || createToastContainer();

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
    return container;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// API Functions
// ============================================

async function getCameras() {
    return await apiRequest('/cameras');
}

async function getLocations() {
    return await apiRequest('/locations');
}

async function createLocation(name) {
    return await apiRequest('/locations', {
        method: 'POST',
        body: JSON.stringify({ name })
    });
}

async function getLocationStatus(locationId) {
    return await apiRequest(`/locations/${locationId}/status`);
}

async function getEvents(limit = 100) {
    return await apiRequest(`/events?limit=${limit}`);
}

async function updateCamera(cameraId, data) {
    return await apiRequest(`/cameras/${cameraId}`, {
        method: 'PATCH',
        body: JSON.stringify(data)
    });
}

async function deleteCamera(cameraId) {
    return await apiRequest(`/cameras/${cameraId}`, {
        method: 'DELETE'
    });
}

async function createCamera(data) {
    return await apiRequest('/cameras', {
        method: 'POST',
        body: JSON.stringify(data)
    });
}

async function captureFrame(streamUrl) {
    return await apiRequest('/cameras/capture-frame', {
        method: 'POST',
        body: JSON.stringify({ stream_url: streamUrl })
    });
}

// ============================================
// DOM Ready & Version Injection
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // Inject version into footer
    const versionEl = document.getElementById('app-version');
    if (versionEl) {
        versionEl.textContent = `v${APP_VERSION}`;
    }

    // Set active nav tab based on current page
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    document.querySelectorAll('.nav-tab').forEach(tab => {
        const tabPage = tab.getAttribute('href');
        if (tabPage === currentPage || (currentPage === '' && tabPage === 'index.html')) {
            tab.classList.add('active');
        }
    });
});

// ============================================
// Tab Switching (for Data Inspector)
// ============================================

function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.dataset.tab;

            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            document.getElementById(targetId).classList.add('active');
        });
    });
}

// ============================================
// Auto-Refresh Manager
// ============================================

class AutoRefresh {
    constructor(callback, intervalMs = 10000) {
        this.callback = callback;
        this.intervalMs = intervalMs;
        this.intervalId = null;
    }

    start() {
        this.callback(); // Initial load
        this.intervalId = setInterval(() => this.callback(), this.intervalMs);
    }

    stop() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }
}
