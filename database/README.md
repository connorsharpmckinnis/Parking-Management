# Database Service

## 🗄️ Role
The "Memory" and "Policy" store. We move away from SQLite and towards a robust SQL engine (PostgreSQL recommended for production) that can handle concurrent writes, timestamps, and data retention policies.

## 📋 Responsibilities
1.  **Persistence**: Stores all configuration and historical data.
2.  **Integrity**: Enforces foreign keys (e.g., an Event must belong to a valid Camera).
3.  **Concurrency**: Handles writes from the Ingest Service while simultaneously serving reads to the Control Plane/UI.

## 🛠 Tech Stack
-   **Engine**: PostgreSQL 15+ (Production) / SQLite (Dev/POC only)
-   **ORM**: SQLAlchemy (Python)
-   **Migrations**: Alembic

## 🏗 Schema (Conceptual)

### Table: `cameras`
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID (PK) | Immutable unique identifier |
| `name` | VARCHAR | Human readable name |
| `connection_string` | TEXT | Encrypted/Hidden RTSP URL |
| `zone_config` | JSONB | Polygon definitions |
| `desired_state` | ENUM | `running`, `stopped`, `maintenance` |
| `created_at` | TIMESTAMP | Audit |

### Table: `occupancy_events`
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | BIGINT (PK) | Auto-incrementing ID |
| `camera_id` | UUID (FK) | Reference to `cameras` |
| `timestamp` | TIMESTAMP | UTC time of observation |
| `occupied_count` | INTEGER | Number of cars detected |
| `raw_data` | JSONB | Full confidence scores / bounding boxes (optional) |

### Table: `health_logs`
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | BIGINT (PK) | |
| `camera_id` | UUID (FK) | |
| `status` | ENUM | `healthy`, `degraded`, `disconnected` |
| `message` | TEXT | Error details ("RTSP timeout") |
| `timestamp` | TIMESTAMP | |

## 🧪 Scenarios & Requirements

### Scenario A: Historical Analysis
**Requirement**: Allow queries for "Average occupancy of North Lot on Tuesdays".
- The schema must support efficient time-range queries (Index on `timestamp` and `camera_id`).

### Scenario B: Data Retention
**Requirement**: Don't fill the disk forever.
- A scheduled job (likely in the Database itself or Orchestrator) deletes `occupancy_events` older than 90 days.
