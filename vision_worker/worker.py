import cv2
import time
import os
import json
import requests
import threading
from datetime import datetime, timezone
from ultralytics import YOLO
import numpy as np
import base64
try:
    from sahi import AutoDetectionModel
    from sahi.predict import get_sliced_prediction
    SAHI_AVAILABLE = True
except ImportError:
    SAHI_AVAILABLE = False

class VisionWorker:
    def __init__(self):
        # Configuration from Environment Variables
        self.camera_id = os.getenv("CAMERA_ID")
        self.stream_url = os.getenv("STREAM_URL")
        self.api_endpoint = os.getenv("API_ENDPOINT") # http://control-plane:8000
        self.interval = float(os.getenv("POLL_INTERVAL", "5.0"))
        self.model_path = os.getenv("MODEL_PATH", "yolo26x.pt")
        
        # Advanced Vision Config
        self.conf_threshold = float(os.getenv("DETECTION_CONFIDENCE", "0.25"))
        self.use_sahi = os.getenv("SAHI_ENABLED", "false").lower() == "true"
        self.sahi_tile_size = int(os.getenv("SAHI_TILE_SIZE", "640"))
        self.sahi_overlap_ratio = float(os.getenv("SAHI_OVERLAP_RATIO", "0.25"))
        
        if self.use_sahi and not SAHI_AVAILABLE:
            print("WARNING: SAHI enabled but not installed. Falling back to standard YOLO.")
            self.use_sahi = False
        
        # Geometry parsing
        zone_json = os.getenv("ZONE_CONFIG", "[]")
        self.polygons = self._parse_zones(zone_json)
        self.total_slots = len(self.polygons)
        
        # Class filtering
        try:
            self.classes = json.loads(os.getenv("DETECTION_CLASSES", "[2, 3, 5, 7]"))
        except:
            self.classes = [2, 3, 5, 7]
        
        self.running = False
        self.latest_frame = None
        self.lock = threading.Lock()
        
        # Initial config fetch
        self._fetch_remote_config()


    def _parse_zones(self, zone_json):
        try:
            if isinstance(zone_json, str):
                data = json.loads(zone_json)
            else:
                data = zone_json
                
            zones = []
            for i, item in enumerate(data):
                pts = np.array(item["points"], np.int32).reshape((-1, 1, 2))
                # Use provided 'id' or default to index-based ID
                spot_id = item.get("id", f"spot_{i+1}")
                zones.append({"id": spot_id, "poly": pts})
            return zones
        except Exception as e:
            print(f"Error parsing zones: {e}")
            return []

    def _fetch_remote_config(self):
        """Fetch latest geometry from Control Plane."""
        if not self.api_endpoint or not self.camera_id:
            return

        try:
            url = f"{self.api_endpoint}/cameras/{self.camera_id}"
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                # Update geometry if present
                if "geometry" in data:
                    new_polys = self._parse_zones(data["geometry"])
                    if new_polys:
                        self.polygons = new_polys
                        self.total_slots = len(self.polygons)
                        print(f"Config updated: {self.total_slots} zones loaded.")
        except Exception as e:
            print(f"Config fetch failed: {e}")


    def start(self):
        self.running = True
        # Start capture thread
        threading.Thread(target=self._capture_loop, daemon=True).start()
        # Start processing loop
        self._process_loop()

    def _capture_loop(self):
        cap = cv2.VideoCapture(self.stream_url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        while self.running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(2)
                cap.release()
                cap = cv2.VideoCapture(self.stream_url)
                continue
            with self.lock:
                self.latest_frame = frame
        cap.release()

    def _process_loop(self):
        print(f"Worker for {self.camera_id} starting...")
        
        model = None
        if self.use_sahi:
            print(f"Initializing SAHI model (tile={self.sahi_tile_size}, overlap={self.sahi_overlap_ratio})...")
            try:
                model = AutoDetectionModel.from_pretrained(
                    model_type='ultralytics',
                    model_path=self.model_path,
                    confidence_threshold=self.conf_threshold,
                    device='cpu' # Assume CPU for container compatibility unless specified
                )
            except Exception as e:
                print(f"Failed to load SAHI model: {e}")
                self.use_sahi = False
        
        if not self.use_sahi:
            model = YOLO(self.model_path)
        
        last_report = 0
        last_config_check = 0
        config_interval = 15.0 # Check for config changes every 15s

        while self.running:
            now = time.time()
            
            # Periodically check for config updates
            if now - last_config_check >= config_interval:
                self._fetch_remote_config()
                last_config_check = now

            if now - last_report >= self.interval:
                with self.lock:
                    frame = self.latest_frame.copy() if self.latest_frame is not None else None
                
                if frame is not None:
                    self._analyze_and_report(model, frame)
                    last_report = time.time()
                else:
                    self._send_heartbeat("degraded", "No frames captured")
            
            time.sleep(0.5)

    def _analyze_and_report(self, model, frame):
        occupied_count = 0
        spot_results = []
        
        detections = [] # List of [x1, y1, x2, y2, conf, cls]
        
        annotated_frame = frame.copy()
        
        try:
            if self.use_sahi:
                result = get_sliced_prediction(
                    frame,
                    model,
                    slice_height=self.sahi_tile_size,
                    slice_width=self.sahi_tile_size,
                    overlap_height_ratio=self.sahi_overlap_ratio,
                    overlap_width_ratio=self.sahi_overlap_ratio,
                    verbose=0
                )
                # Convert SAHI results to standard format
                for obj in result.object_prediction_list:
                    if obj.category.id in self.classes:
                        bbox = obj.bbox
                        # SAHI bbox is [minx, miny, maxx, maxy]
                        detections.append([int(bbox.minx), int(bbox.miny), int(bbox.maxx), int(bbox.maxy), obj.score.value, obj.category.id])
                        
                # Draw boxes manually for SAHI
                for det in detections:
                     cv2.rectangle(annotated_frame, (det[0], det[1]), (det[2], det[3]), (255, 0, 0), 2)
            else:
                # Standard YOLO
                results = model.predict(frame, classes=self.classes, conf=self.conf_threshold, verbose=False)
                if results:
                    boxes = results[0].boxes
                    #annotated_frame = results[0].plot() # Use Ultralytics plotter
                    annotated_frame = frame.copy()
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        conf = box.conf[0].cpu().numpy()
                        cls = box.cls[0].cpu().numpy()
                        detections.append([int(x1), int(y1), int(x2), int(y2), float(conf), int(cls)])

            # Occupancy Logic (Bottom-Center)
            for zone in self.polygons:
                poly = zone["poly"]
                spot_id = zone["id"]
                is_occupied = False
                
                for det in detections:
                    x1, y1, x2, y2, conf, cls = det
                    # Bottom-center point
                    bx = int((x1 + x2) / 2)
                    by = int(y2)

                    cv2.circle(
                        annotated_frame,
                        (bx, by),
                        radius=7,              # visible, not subtle
                        color=(255, 0, 255),     # yellow (BGR)
                        thickness=-1           # filled circle
                    )
                    
                    if cv2.pointPolygonTest(poly, (bx, by), False) >= 0:
                        is_occupied = True
                        break
                
                spot_results.append({
                    "spot_id": spot_id,
                    "occupied": is_occupied
                })
                
                if is_occupied:
                    occupied_count += 1
                
                # Draw parking spot polygon
                color = (0, 0, 255) if is_occupied else (0, 255, 0)
                cv2.polylines(annotated_frame, [poly], True, color, 2)

            _, buffer = cv2.imencode('.jpg', annotated_frame)
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            
        except Exception as e:
            print(f"Inference error: {e}")
            jpg_as_text = None

        # POST Telemetry
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "occupied_count": occupied_count,
            "free_count": self.total_slots - occupied_count,
            "total_slots": self.total_slots,
            "metadata_json": {
                "spot_details": spot_results,
                "snapshot": jpg_as_text
            }
        }
        
        try:
            url = f"{self.api_endpoint}/cameras/{self.camera_id}/event"
            requests.post(url, json=payload, timeout=5)
            print(f"Reported: {occupied_count}/{self.total_slots} (with per-spot data)")
        except Exception as e:
            print(f"Failed to report: {e}")

    def _send_heartbeat(self, status, msg=""):
        try:
            url = f"{self.api_endpoint}/cameras/{self.camera_id}/heartbeat"
            requests.post(url, json={"status": status, "message": msg}, timeout=2)
        except:
            pass

if __name__ == "__main__":
    worker = VisionWorker()
    worker.start()
