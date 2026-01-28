# Municipal Parking & Security Vision System

This project is a microservices-based system designed to manage city-wide parking occupancy and security cameras using computer vision.

## 🏗️ Architecture Overview

The system is composed of 6 distinct services:

1.  **[Dashboard](./dashboard/README.md)**: Standardized UI for monitoring and management.
2.  **[Control Plane](./control_plane/README.md)**: The "Brain". Authority for configurations and management API.
3.  **[Ingest Service](./ingest_service/README.md)**: The data gatekeeper. Receives and persists telemetry (events/heartbeats).
4.  **[Vision Worker](./vision_worker/README.md)**: The "Eye". Scans streams and reports occupancy. Supports NVIDIA GPU acceleration.
5.  **[Orchestrator](./orchestrator/README.md)**: The "Operator". Reconciles DB intent with running worker containers.
6.  **[Database](./database/README.md)**: PostgreSQL storage for metadata and history.

## 🚀 Key Features

- **Standalone Ingest**: Decoupled telemetry handling for horizontal scalability.
- **GPU Acceleration**: Vision workers utilize NVIDIA GPUs for high-speed YOLO inference.
- **Power BI Exports**: Dedicated analytics endpoints for CSV/JSON data extracts.
- **Consolidated UI**: Centralized sidebar and navigation management.

## 📂 Project Structure

```
/
├── control_plane/   # Authority & Master API
├── dashboard/       # Web UI (FastAPI static server)
├── ingest_service/  # Telemetry Receiver
├── vision_worker/   # AI Inference (YOLO / SAHI)
├── database/        # PostgreSQL Schema & shared models
├── orchestrator/    # Lifecycle management loop
└── compose.yaml     # System orchestration
```

## 🛠️ Getting Started

1.  **Prerequisites**: 
    - Docker / Docker Desktop
    - NVIDIA Container Toolkit (for GPU support)
    - Python 3.11+
2.  **Startup**:
    ```bash
    docker compose up -d --build
    ```
3.  **Access**:
    - Dashboard: `http://localhost:8501`
    - Control Plane API: `http://localhost:8002` (internal 8000)
    - Ingest Service: `http://localhost:8003` (internal 8001)

## 📜 Development
See internal READMEs for specific service documentation and API contracts.
