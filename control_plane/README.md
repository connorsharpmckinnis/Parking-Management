# Control Plane Service

## 🧠 Role
The "Brain" of the system. It is the authoritative source of truth for all camera configurations and the primary interface for system administrators. It **never** processes video frame data directly.

## 📋 Responsibilities
1.  **Camera Registry**: centralized CRUD for camera metadata (IP, credentials, location, model config).
2.  **State Management**: maintains the `desired_state` (Running/Stopped) for each camera.
3.  **Telemetry Ingest** (Temporary): Acts as the HTTP receiver for events from `vision_worker` containers until the standalone Ingest Service is spun out.
4.  **API Gateway**: Provides a REST API for the UI and CLI tools.

## 🛠 Tech Stack
-   **Language**: Python 3.11+
-   **Framework**: FastAPI
-   **Database**: PostgreSQL (via SQLAlchemy/AsyncPG) - *Uses SQLite for Dev/POC*

## 🔌 API Contract (Draft)

### `GET /cameras`
Returns list of all registered cameras.
```json
[
  {
    "id": "uuid",
    "name": "North Lot Entrance",
    "status": "healthy",
    "desired_state": "running"
  }
]
```

### `POST /cameras`
Register a new camera.
**Body:**
```json
{
  "name": "South Gate",
  "connection_string": "rtsp://user:pass@10.0.0.5:554/stream",
  "zone_config": { ...json_geometry... }
}
```

### `POST /telemetry/{camera_id}`
Endpoint for workers to push data.
**Body:**
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "occupancy": 5,
  "confidence": 0.95
}
```

## 🧪 Scenarios & Requirements

### Scenario A: New Camera Installation
**Requirement**: Admin must be able to register a camera without restarting the system.
1.  Admin POSTs to `/cameras` with connection details.
2.  System validates the RTSP string format (regex only, no connection attempt).
3.  System saves record with `desired_state="stopped"` (default safety).
4.  System returns `201 Created` with the new UUID.

### Scenario B: Operator "Pauses" a Camera
**Requirement**: Stop processing specific streams during maintenance.
1.  Operator PATCHes `/cameras/{id}` setting `desired_state="stopped"`.
2.  (Orchestrator will see this and kill the container - out of scope for Control Plane, but CP must persist the flag).

### Scenario C: Worker Reporting
**Requirement**: High-volume ingestion.
1.  Worker POSTs occupancy data.
2.  Control Plane validates `camera_id` exists.
3.  Control Plane updates `last_contact` timestamp for that camera.
4.  Control Plane forwards data to DB.
