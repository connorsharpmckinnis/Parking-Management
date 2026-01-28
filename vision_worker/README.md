# Vision Worker Service

## 👁️ Role
The "Eye". A stateless container that processes a single camera stream. It detects vehicles, maps them to parking spots, and heartbeats health data.

## 📋 Responsibilities
1.  **Inference**: Runs YOLO26 on video frames for vehicle detection.
2.  **SAHI Support**: Optional "Slicing Aided Hyper Inference" for high-resolution streams or distance detection.
3.  **Polygon Mapping**: Determines if a bounding box overlaps with a defined parking spot.
4.  **Decoupled Reporting**: Sends data to the `Ingest Service` and fetches config from the `Control Plane`.

## 🛠 Tech Stack
-   **Base Image**: `ultralytics/ultralytics:latest` (GPU-optimized)
-   **Vision Engine**: PyTorch + CUDA + OpenCV
-   **Libraries**: `ultralytics`, `sahi`, `requests`

## ⚙️ Configuration (Environment)
Managed by the `Orchestrator`.

| Variable | Description | Example |
| :--- | :--- | :--- |
| `CAMERA_ID` | UUID of this camera | `550e8400...` |
| `STREAM_URL` | RTSP/HTTP Source | `rtsp://user:pass@10.0.0.5` |
| `INGEST_URL` | Ingest API root | `http://ingest-service:8001` |
| `CONFIG_URL` | Control Plane root | `http://control-plane:8000` |
| `NVIDIA_VISIBLE_DEVICES` | GPU Visibility | `all` |

## 🚀 GPU Acceleration
To utilize hardware acceleration, the host must have:
1. NVIDIA Drivers installed.
2. `nvidia-container-toolkit` installed and configured in Docker.
3. Use the `--runtime nvidia` and `--ipc host` flags (managed by Orchestrator).

## 🧪 Status Logic
- **Healthy**: Active heartbeats every ~60s.
- **Degraded**: No heartbeat for > 5 minutes (threshold relaxed for network jitter).
- **Disconnected**: No heartbeat for > 10 minutes.
