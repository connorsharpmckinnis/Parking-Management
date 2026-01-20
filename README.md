# Municipal Parking & Security Vision System

## 🏗️ Architecture Overview

This project is a microservices-based system designed to manage city-wide security cameras and perform edge/centralized computer vision analysis.

The system is composed of 5 distinct services:

1.  **[Control Plane](./control_plane/README.md)**: The HTTP API and Management UI. The source of truth.
2.  **[Vision Worker](./vision_worker/README.md)**: The "dumb" worker. One container per camera. Connects, detects, and reports.
3.  **[Ingest Service](./ingest_service/README.md)**: The data gatekeeper. Validates and writes telemetry to storage.
4.  **[Database](./database/README.md)**: PostgreSQL schema and storage policies.
5.  **[Orchestrator](./orchestrator/README.md)**: The background loop that manages the lifecycle of Vision Workers based on Control Plane intent.

## 📂 Project Structure

```
/
├── control_plane/   # Authority & API
├── vision_worker/   # AI Inference Logic
├── ingest_service/  # High-volume Telemetry Receiver
├── database/        # SQL Schema & Migrations
├── orchestrator/    # Container Management Loop
├── proof_of_concept/ # Legacy V0 Demo code
└── README.md        # This file
```

## 🚀 Getting Started

*(Instructions will be populated as services are implemented)*

1.  **Prerequisites**: Podman (or Docker), Python 3.11+.
2.  **Setup**:
    ```bash
    docker-compose up -d
    ```

## 📜 Development Implementation Plan
See `implementation_plan.md` and `walkthrough.md` in the artifacts folder for the current build status and testing guide.
