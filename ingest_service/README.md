# Ingest Service

## 🛡️ Role
The "Gatekeeper". A high-throughput buffer that sits between the wild internet/cameras and the pristine database. It ensures that the database is never overwhelmed and that bad data is rejected early.

> **Note for Phase 1**: This logic will physically reside inside the `control_plane` container to simplify deployment, but it is architecturally distinct. We define it here to prepare for Phase 2 implementation.

## 📋 Responsibilities
1.  **Schema Validation**: Ensures incoming JSON payloads match the expected format (v1.0 telemetry).
2.  **Authentication**: Verifies that the poster has a valid API token (or is an allowed container ID).
3.  **Sanitization**: Normalizes timestamps to UTC.
4.  **Writes**: Batches or directly inserts records into the `occupancy_events` table.

## 🧪 Scenarios & Requirements

### Scenario A: Data Spam
**Requirement**: Protect the DB from a malfunctioning worker loop.
1.  A worker glitched and is sending 100 requests per second.
2.  Ingest Service detects rate limit violation (e.g., > 1 req/sec per Camera ID).
3.  Ingest Service returns `429 Too Many Requests`.
4.  Database is unaffected.

### Scenario B: Schema Evolution
**Requirement**: Handle legacy agents.
1.  Worker V1 sends payload `{ "cars": 5 }`.
2.  Worker V2 sends payload `{ "occupied": 5, "trucks": 1 }`.
3.  Ingest Service maps both to the canonical DB schema, filling defaults where necessary.

### Scenario C: Database Outage
**Requirement**: No data loss (start of queuing architecture).
1.  Database connection fails.
2.  Ingest Service cannot write.
3.  (Edge/V2): Ingest Service buffers messages to Redis/Kafka.
4.  (Phase 1): Ingest Service returns `503 Service Unavailable`, forcing the Worker to retry later.
