# Parking Management & Vision Monitoring System

A lightweight, real-time parking occupancy detection system using YOLOv11 and Computer Vision. This project provides a web-based dashboard for configuring camera streams, defining parking boundaries, and logging occupancy data.

## 🚀 Core Components

### 1. `select_points.py`
**The Configuration Tool.** 
Used to define the "zones of interest" (parking spots). It launches a GUI where you can draw polygons over a reference frame. This generates `bounding_boxes.json`, which the monitoring system uses to check for vehicle presence.

### 2. `monitor.py`
**The Engine.**
Contains the `ParkingMonitor` class, which handles:
- **Dual-Threaded Operation**: One thread captures frames from the RTSP/HTTP stream as fast as possible (ensuring smooth playback), while a second thread performs heavy AI inference at a set interval.
- **Inference**: Uses YOLOv11 to detect vehicles (cars, trucks, motorcycles, buses).
- **Geometric Hit-Testing**: Performs a "Point-in-Polygon" test to determine if a detected vehicle's center point lies within a defined parking spot.
- **Annotation**: Overlays occupancy counts and countdown timers onto the live feed.

### 3. `main.py`
**The Interface.**
A FastAPI-based web server that provides:
- A dashboard to input camera credentials and IP addresses.
- Multi-part streaming of the analyzed video feed.
- Display of recent occupancy logs.

### 4. `db.py`
**The Data Store.**
A simplified SQLite implementation to log `timestamp`, `occupied_count`, and `free_count`.

---

## 📈 Scaling to Municipal Monitoring

To evolve this into a lightweight monitoring system for a full security camera network, we suggest a decoupled architecture.

### Architecture A: Centralized Processing (High Bandwidth/Fiber)
Best for cameras connected via high-speed fiber where low camera-side power is a priority.
- **Deployment**: A single high-performance server (GPU-ready) running many instances of the `monitor.py` logic.
- **Workflow**: 
    1. Use the current UI to "onboard" a camera and generate its JSON config.
    2. Spin up a headless Docker container for that specific Camera ID.
    3. The container pulls the high-res stream and processes it centrally.

### Architecture B: Edge Processing (Low Bandwidth/MQTT)
Best for distributed systems or cameras on constrained networks.
- **Deployment**: Lightweight SBCs (e.g., NVIDIA Jetson, Raspberry Pi + Coral TPU) installed near the camera.
- **Workflow**:
    1. The Edge device runs a stripped-down `monitor.py` (no UI/web server).
    2. **Local Caching**: Logs data to a local SQLite database (for resilience against network drops).
    3. **MQTT Publication**: Publishes occupancy updates to a central broker (e.g., Mosquitto) whenever counts change.
    4. **Health Checks**: Sends "heartbeat" messages via MQTT to a central monitoring portal.

---

## 🛠️ Future Roadmap

1. **Decouple UI**: Transform this project into a "Configuration Utility" used only by setup technicians to produce a standard `config.yaml` containing the stream URL and boundary JSON.
2. **Service Orchestration**: Create a secondary project (e.g., `Camera-Manager`) that reads these configs and manages the lifecycle of monitoring workers (using Systemd or Podman).
3. **MQTT Integration**: Replace the current `db.log_data` call with a flexible `Publisher` class that can handle both SQLite and MQTT messages.

## ⚙️ Installation

```powershell
# Create environment
uv venv
source .venv/Scripts/activate

# Install requirements
pip install -r requirements.txt

# Start system
uv run main.py
```
