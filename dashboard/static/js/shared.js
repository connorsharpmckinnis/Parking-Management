/**
 * Parking Management Dashboard - Shared JavaScript
 * Town of Apex | v0.8.2
 */

const APP_VERSION = '0.8.2';
const CONTROL_PLANE_URL = 'http://localhost:8000'; // Direct access for local dev

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

async function getStats() {
    return await apiRequest('/stats');
}

async function createLocation(name) {
    return await apiRequest('/locations', {
        method: 'POST',
        body: JSON.stringify({ name })
    });
}

async function deleteLocation(locationId) {
    return await apiRequest(`/locations/${locationId}`, {
        method: 'DELETE'
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

async function getCameraSnapshot(cameraId) {
    return await apiRequest(`/cameras/${cameraId}/snapshot`);
}

async function captureFrame(streamUrl) {
    return await apiRequest('/cameras/capture-frame', {
        method: 'POST',
        body: JSON.stringify({ stream_url: streamUrl })
    });
}

async function getSpots() {
    return await apiRequest('/spots');
}

async function getSpotHistory(spotId, limit = 50) {
    return await apiRequest(`/spots/${spotId}/history?limit=${limit}`);
}

async function deleteSpot(spotId) {
    return await apiRequest(`/spots/${spotId}`, {
        method: 'DELETE'
    });
}

// ============================================
// UI Components
// ============================================

/**
 * Standardized Sidebar Implementation
 */
function initSidebar() {
    const sidebarTarget = document.getElementById('sidebar-target');
    if (!sidebarTarget) return;

    const currentPage = window.location.pathname.split('/').pop() || 'index.html';

    // Normalize index/root
    const activePage = (currentPage === '' || currentPage === '/') ? 'index.html' : currentPage;

    const sidebarHtml = `
    <nav class="sidebar">
        <div class="sidebar-header">
            <div class="sidebar-logo-icon"><i data-lucide="camera"></i></div>
            <div class="sidebar-brand">PeakPark<span>Occupancy Detection</span></div>
        </div>
        <div class="sidebar-nav">
            <div class="nav-section-label">Overview</div>
            <a href="index.html" class="nav-item ${activePage === 'index.html' ? 'active' : ''}">
                <i data-lucide="layout-dashboard" class="navbar-icon"></i>Dashboard
            </a>
            
            <div class="nav-section-label">Management</div>
            <a href="cameras.html" class="nav-item ${activePage === 'cameras.html' ? 'active' : ''}">
                <i data-lucide="camera" class="navbar-icon"></i>Cameras
            </a>
            <a href="monitor.html" class="nav-item ${activePage === 'monitor.html' ? 'active' : ''}">
                <i data-lucide="monitor-play" class="navbar-icon"></i>Live Monitor
            </a>
            
            <div class="nav-section-label">Analytics</div>
            <a href="locations.html" class="nav-item ${activePage === 'locations.html' ? 'active' : ''}">
                <i data-lucide="map-pin" class="navbar-icon"></i>Locations
            </a>
            <a href="analytics.html" class="nav-item ${activePage === 'analytics.html' ? 'active' : ''}">
                <i data-lucide="download" class="navbar-icon"></i>Data Export
            </a>
            <a href="inspector.html" class="nav-item ${activePage === 'inspector.html' ? 'active' : ''}">
                <i data-lucide="database" class="navbar-icon"></i>Database
            </a>
        </div>
        <div class="sidebar-footer">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span id="app-version">v${APP_VERSION}</span>
                <a href="#" class="text-muted"><i data-lucide="help-circle" style="width:14px;"></i></a>
            </div>
            <div style="margin-top: 0.5rem; font-size: 0.7rem; color: var(--muted-foreground); opacity: 0.6;">
                Town of Apex IT Innovations
            </div>
        </div>
    </nav>
    `;

    sidebarTarget.innerHTML = sidebarHtml;
}

// ============================================
// DOM Ready & Global Initialization
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Sidebar
    initSidebar();

    // 2. Initialize Icons (Lucide)
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
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
