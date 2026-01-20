# Vision Worker Service

## 👁️ Role
The "Eye" of the system. A stateless, single-purpose worker container. One instance runs per camera stream. It does exactly one thing: pulls frames, counts cars, and reports the number.

## 📋 Responsibilities
1.  **Stream Connection**: Maintains a robust connection to **one** RTSP/HTTP video source.
2.  **Inference**: Runs YOLO 11 (or configured model) on frames.
3.  **Geometry Check**: Maps detections to specific parking zones (polygons).
4.  **Reporting**: Sends HTTP POST requests to the `Control Plane` (or `Ingest Service`) with results.
5.  **Heartbeat**: Periodically reports "I am alive" even if no cars are moving.

## 🛠 Tech Stack
-   **Language**: Python 3.11+
-   **Vision**: OpenCV (headless), Ultralytics YOLO
-   **Hardware Acceleration**: CUDA (if GPU avail) or CPU (OpenVINO/ONNX optimized)

## ⚙️ Configuration (Environment Variables)
The worker is configured **exclusively** via environment variables. It has no local config file.

| Variable | Description | Example |
| :--- | :--- | :--- |
| `CAMERA_ID` | UUID of the camera this worker serves | `550e8400-e29b-41d4-a716...` |
| `STREAM_URL` | Full RTSP/HTTP connection string | `rtsp://admin:pass@192.168.1.50` |
| `API_ENDPOINT` | URL of the Ingest/Control service | `http://control-plane:8000/telemetry` |
| `POLL_INTERVAL` | Seconds between inference checks | `5.0` |
| `ZONE_CONFIG` | JSON string of polygon coordinates | `[{"points": [[0,1], [1,1]...]}]` |

## 🧪 Scenarios & Requirements

### Scenario A: Network Drop
**Requirement**: The worker must not crash if the camera goes offline.
1.  `cv2.read()` returns empty/false.
2.  Worker logs "lost connection".
3.  Worker enters a retry loop (exponential backoff: 2s, 4s, 8s...).
4.  Worker sends "Heartbeat" with status `degraded` to Control Plane if possible.

### Scenario B: Boot Sequence
**Requirement**: Fast startup.
1.  Container starts.
2.  Loads YOLO model into memory (RAM).
3.  Parses `ZONE_CONFIG` from env var.
4.  Connects to RTSP stream.
5.  Sends first "Heartbeat" to Control Plane -> "Healthy".

### Scenario C: Blocked View
**Requirement**: Non-fatal error reporting.
1.  Vision logic detects "black screen" or "camera occlusion" (optional advanced feature).
2.  Worker continues loop but flags data quality as `low_confidence`.
