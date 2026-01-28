# Dashboard Service

## 🎨 Role
The "Visualizer". A standardized interface for system monitoring, camera management, and data analysis.

## 📋 Responsibilities
1.  **System Monitoring**: Real-time stats on camera health and parking occupancy.
2.  **Camera & Location CRUD**: Interface for managing the physical layout of the system.
3.  **Data Analytics**: Interface for querying and exporting historical data for Power BI.
4.  **Live Monitor**: Low-latency preview of active camera streams.

## 🛠 Tech Stack
-   **Backend**: FastAPI (Static file server & API proxy)
-   **Frontend**: Vanilla JS / HTML5 / Lucide Icons
-   **CSS**: Vanilla CSS with a modern design system.

## 🧱 UI Architecture (Consolidated)
The dashboard uses a standardized component system managed via `shared.js`.

### Shared Sidebar
The sidebar is injected dynamically at runtime into `<div id="sidebar-target"></div>`.
- **Logic**: Managed in `initSidebar()`.
- **Navigation**: Centrally defined links with automatic "Active" state detection based on the URL path.

### Shared Branding
Branding, versioning, and tooltips are injected globally from `shared.js`, ensuring a consistent "PeakPark" experience across all pages.

## 📊 Analytics Section
The Analytics page features a tabbed interface for high-performance data exports:
- **Tab A: Observations**: Joined occupancy data (IDs, Names, Timestamps).
- **Tab B: Health**: Camera uptime and status logs.
- **Export Formats**: Standard CSV (optimized for Power BI) and JSON.
