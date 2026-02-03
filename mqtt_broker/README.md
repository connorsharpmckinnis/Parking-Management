# MQTT Broker Service

## 📡 Role
The "Central Hub". This service provides a lightweight message broker (Eclipse Mosquitto) that acts as the entry point for telemetry from edge-based vision workers.

## 📋 Responsibilities
1.  **Message Routing**: Receives asynchronous telemetry from edge devices and routes it to subscribers.
2.  **Edge Decoupling**: Allows edge devices to "fire and forget" telemetry without needing a stable persistent connection to the primary Ingest Service.
3.  **Protocol Support**: Provides standard MQTT/MQTTS connectivity for low-bandwidth cellular devices.

## 🛠 Tech Stack
-   **Broker**: [Eclipse Mosquitto](https://mosquitto.org/)
-   **Containerize**: Alpine-based Docker image for minimal footprint.

## 🧵 Topic Structure
Edge devices should publish to the following topics:

| Topic | Description | Payload |
| :--- | :--- | :--- |
| `parking/camera/{id}/event` | Occupancy telemetry | `OccupancyUpdate` JSON |
| `parking/camera/{id}/heartbeat` | Health/Status updates | `HealthUpdate` JSON |

## 🔗 Integration (The Bridge)
To get MQTT data into our PostgreSQL database, we use the **[Ingest Bridge](../ingest_bridge/main.py)** service:
-   **Bridge Service**: A lightweight Python service that subscribes to `parking/camera/+/+`.
-   **Processing**: For every message received, it forwards the payload via HTTP POST to the `ingest_service`.
-   **Container Name**: `parking-ingest-bridge`

## 🚀 Getting Started
The broker is initialized via `compose.yaml`. Standard port is `1883`.