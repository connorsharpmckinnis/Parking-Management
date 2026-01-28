# Control Plane Service

## 🧠 Role
The "Brain" and Authority. It manages camera configurations, locations, and the overall system state. It provides the REST API for the Dashboard and Orchestrator.

## 📋 Responsibilities
1.  **System Authority**: Master registry for cameras, locations, and spots.
2.  **Configuration API**: Serves desired state and computer vision parameters to the Orchestrator/Workers.
3.  **Analytics Engine**: Joins historical occupancy data with location/spot metadata for reporting.
4.  **Security**: Manages access to system-wide settings.

## 🔌 API Contract Highlights

### 📊 Analytics & Reporting

#### `GET /analytics/observations`
Export spot occupancy history with joined names (Location/Spot/Camera).
- **Params**: `location_id`, `start_date`, `end_date`, `format` (csv/json).
- **Usage**: Primary endpoint for Power BI dashboards.

#### `GET /analytics/health`
Export camera status and health log history.
- **Params**: `camera_id`, `start_date`, `end_date`, `format` (csv/json).
- **Usage**: Uptime auditing and reliability analysis.

### 🎥 Camera Management

#### `GET /cameras`
Returns list of all registered cameras with computed statuses.

#### `POST /cameras` / `PATCH /cameras/{id}`
Manages camera metadata, `desired_state` (running/stopped), and vision geometry.

### 📍 Location Management

#### `GET /locations` / `POST /locations`
Organizes cameras into logical areas (e.g., "Apex Town Hall").

---

## 🛠 Tech Stack
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Database**: PostgreSQL (via SQLAlchemy)

> **Note**: Telemetry ingestion (heartbeats/events) has been migrated to the standalone `ingest_service` to maintain Control Plane responsiveness.
