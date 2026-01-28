# Ingest Service

## 🛡️ Role
The "Gatekeeper". A high-throughput service that handles all incoming telemetry from Vision Workers. It validates data and persists it to the database, protecting the Control Plane from high-volume write traffic.

## 📋 Responsibilities
1.  **Event Processing**: Receives occupancy counts and spot-level observations.
2.  **Heartbeat Monitoring**: Tracks camera liveness and status tags (Healthy, Degraded, etc.).
3.  **Spot Mapping**: Maps raw detections from workers to official `SpotObservation` records.
4.  **Database Decoupling**: Ensures that high-frequency telemetry doesn't impact management API performance.

## 🔌 API Contract

### `POST /cameras/{id}/event`
Receive occupancy counts and metadata.
- **Body**: `{ "timestamp": "...", "occupied_count": X, "free_count": Y, "metadata_json": {...} }`

### `POST /cameras/{id}/heartbeat`
Receive health stayus update.
- **Body**: `{ "status": "healthy", "message": "..." }`

## 🧪 Scenarios & Requirements

### Scenario A: High-Frequency Scaling
**Requirement**: Handle 100+ cameras heartbeating every 60s without latency.
1.  Ingest Service uses asynchronous DB writes.
2.  Control Plane metrics remain stable as it is not involved in this hot path.

### Scenario B: Data Integrity
**Requirement**: Only accept observations for spots that actually exist.
1.  Ingest Service queries the `Spot` table for valid IDs in the camera's location.
2.  Only validates and saves records matching known spot naming conventions.
