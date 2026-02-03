# Edge Processing Service

## 🏎️ Role
The "Local Eye". Unlike the fiber-connected `vision_worker`, this service runs directly on edge hardware (e.g., Jetson Nano, Raspberry Pi) located at the camera site. 

## 📋 Responsibilities
1.  **Local Inference**: Performs vehicle detection on the local camera stream.
2.  **Bandwidth Optimization**: Instead of streaming high-def video to a central server, it only transmits small JSON occupancy updates over MQTT.
3.  **Cellular-Ready**: Designed to handle intermittent connectivity with local caching/retries.

## 🛠 Tech Stack
-   **Language**: Python 3.11+
-   **Communication**: `paho-mqtt`
-   **Vision**: Optimized YOLO/RT-DETR models (TensorRT or ONNX for edge hardware).

## 🧪 Simulation & Development
During development, we use simulation scripts to validate the pipeline without requiring physical edge hardware.

### Simulator: `simulate_edge.py`
A Python script that generates mock occupancy data and publishes it to the `mqtt_broker`.

**Usage:**
```bash
python simulate_edge.py --camera_id <UUID> --broker <IP>
```

### Future Work: `edge_worker.py`
The production-ready container logic that will:
-   Connect to local RTSP stream.
-   Run inference.
-   Map detections to spot geometries.
-   Publish to MQTT.