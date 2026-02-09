import cv2
import time
import os
import json
import requests
import threading
from datetime import datetime, timezone
from ultralytics import YOLO, RTDETR
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
        self.api_endpoint = os.getenv("API_ENDPOINT")  # Telemetry: http://ingest-service:8001
        self.config_endpoint = os.getenv("CONFIG_ENDPOINT", os.getenv("API_ENDPOINT"))  # Config: http://control-plane:8000
        self.interval = float(os.getenv("POLL_INTERVAL", "5.0"))
        self.model_path = os.getenv("MODEL_PATH", "rtdetr-l.pt")
        
        # Advanced Vision Config
        self.conf_threshold = float(os.getenv("DETECTION_CONFIDENCE", "0.25"))
        self.use_sahi = os.getenv("SAHI_ENABLED", "false").lower() == "true"
        self.sahi_tile_size = int(os.getenv("SAHI_TILE_SIZE", "640"))
        self.sahi_overlap_ratio = float(os.getenv("SAHI_OVERLAP_RATIO", "0.25"))
        
        # Sub-BBox Occupancy Logic Config
        self.occupancy_bottom_pct = float(os.getenv("OCCUPANCY_BOTTOM_PCT", "0.33"))
        self.occupancy_min_overlap = float(os.getenv("OCCUPANCY_MIN_OVERLAP", "0.30"))
        
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
        
        # Initialize attributes that will be updated by _fetch_remote_config
        self.model_version = self.model_path 
        self.model = None

        # Initial config fetch
        self._fetch_remote_config()

        self.device = self._get_device()
        print(f"Using device: {self.device}")

    def _load_model(self):
        """Load or Reload the model based on current config."""
        print(f"Loading model: {self.model_path} (SAHI={self.use_sahi})...")
        
        # Cleanup existing model to free VRAM
        if self.model is not None:
            del self.model
            self.model = None
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except:
                pass
            import gc
            gc.collect()

        try:
            if self.use_sahi:
                print(f"Initializing SAHI model (tile={self.sahi_tile_size}, overlap={self.sahi_overlap_ratio})...")
                self.model = AutoDetectionModel.from_pretrained(
                    model_type='ultralytics',
                    model_path=self.model_path,
                    confidence_threshold=self.conf_threshold,
                    device=self.device
                )
            else:
                if "rtdetr" in self.model_path:
                    self.model = RTDETR(self.model_path)
                else:
                    self.model = YOLO(self.model_path)
                
                # Check if .to() is available (YOLO/RTDETR usually handle device in predict or init, but safe to call)
                if hasattr(self.model, 'to'):
                    self.model.to(self.device)
                    
            print(f"Model loaded successfully: {self.model_path}")
        except Exception as e:
            print(f"Failed to load model {self.model_path}: {e}")
            self.model = None

    def _get_device(self):
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"


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
        """Fetch latest config from Control Plane and apply changes."""
        if not self.config_endpoint or not self.camera_id:
            return

        try:
            url = f"{self.config_endpoint}/cameras/{self.camera_id}"
            resp = requests.get(url, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                
                # 1. Update Geometry
                if "geometry" in data:
                    new_polys = self._parse_zones(data["geometry"])
                    if new_polys:
                        self.polygons = new_polys
                        self.total_slots = len(self.polygons)
                
                # 2. Update Processing Config
                if "processing_interval_sec" in data and data["processing_interval_sec"] is not None:
                    new_val = float(data["processing_interval_sec"])
                    if new_val != self.interval:
                        print(f"DEBUG: Config change: Interval {self.interval} -> {new_val}")
                        self.interval = new_val
                    
                if "detection_confidence" in data and data["detection_confidence"] is not None:
                    new_val = float(data["detection_confidence"])
                    if new_val != self.conf_threshold:
                        print(f"DEBUG: Config change: Confidence {self.conf_threshold} -> {new_val}")
                        self.conf_threshold = new_val
                    
                if "occupancy_bottom_pct" in data and data["occupancy_bottom_pct"] is not None:
                    new_val = float(data["occupancy_bottom_pct"])
                    if new_val != self.occupancy_bottom_pct:
                        print(f"DEBUG: Config change: Bottom Pct {self.occupancy_bottom_pct} -> {new_val}")
                        self.occupancy_bottom_pct = new_val
                    
                if "occupancy_min_overlap" in data and data["occupancy_min_overlap"] is not None:
                    new_val = float(data["occupancy_min_overlap"])
                    if new_val != self.occupancy_min_overlap:
                        print(f"DEBUG: Config change: Min Overlap {self.occupancy_min_overlap} -> {new_val}")
                        self.occupancy_min_overlap = new_val

                # 3. Check for Model/SAHI changes triggers reload
                needs_reload = False
                
                # Model Version Update
                new_model = data.get("model_version")
                if new_model and new_model != self.model_version:
                    print(f"Config change: Model version {self.model_version} -> {new_model}")
                    self.model_path = new_model
                    self.model_version = new_model
                    needs_reload = True
                    
                # SAHI Config Update
                new_sahi = data.get("sahi_enabled", False)
                if new_sahi != self.use_sahi:
                    print(f"Config change: SAHI enabled {self.use_sahi} -> {new_sahi}")
                    self.use_sahi = new_sahi
                    if self.use_sahi and not SAHI_AVAILABLE:
                         print("SAHI requested but not available. Ignoring.")
                         self.use_sahi = False
                    else:
                        needs_reload = True
                
                if self.use_sahi:
                    new_tile = int(data.get("sahi_tile_size", self.sahi_tile_size))
                    if new_tile != self.sahi_tile_size:
                        print(f"DEBUG: Config change: SAHI Tile {self.sahi_tile_size} -> {new_tile}")
                        self.sahi_tile_size = new_tile

                    new_overlap = float(data.get("sahi_overlap_ratio", self.sahi_overlap_ratio))
                    if new_overlap != self.sahi_overlap_ratio:
                        print(f"DEBUG: Config change: SAHI Overlap {self.sahi_overlap_ratio} -> {new_overlap}")
                        self.sahi_overlap_ratio = new_overlap
                
                if needs_reload:
                    self._load_model()
                    
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
        
        # Initial model load
        self._load_model()
        
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
                
                if frame is not None and self.model is not None:
                    self._analyze_and_report(self.model, frame)
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

            # Occupancy Logic (Sub-BBox Overlap)
            # For each detection, create a sub-bbox (bottom X%) and find the best overlapping zone.
            # A detection is assigned to the zone with the highest overlap if it exceeds min_overlap.
            
            # Track which zones are occupied (zone_id -> True)
            zone_occupancy = {zone["id"]: False for zone in self.polygons}
            
            for det in detections:
                x1, y1, x2, y2, conf, cls = det
                
                # Create sub-bbox (bottom X% of the detection)
                bbox_height = y2 - y1
                sub_y1 = int(y2 - bbox_height * self.occupancy_bottom_pct)
                sub_bbox_pts = np.array([
                    [x1, sub_y1],
                    [x2, sub_y1],
                    [x2, y2],
                    [x1, y2]
                ], np.int32)
                
                # Draw sub-bbox in magenta
                cv2.polylines(annotated_frame, [sub_bbox_pts], True, (255, 0, 255), 2)
                
                # Calculate sub-bbox area
                sub_bbox_area = (x2 - x1) * (y2 - sub_y1)
                if sub_bbox_area <= 0:
                    continue
                
                # Find the zone with the best overlap
                best_zone_id = None
                best_overlap_ratio = 0.0
                
                for zone in self.polygons:
                    zone_poly = zone["poly"].reshape(-1, 2)
                    
                    # Calculate intersection using cv2.intersectConvexConvex
                    ret, intersection_pts = cv2.intersectConvexConvex(sub_bbox_pts.astype(np.float32), zone_poly.astype(np.float32))
                    
                    if ret > 0 and intersection_pts is not None and len(intersection_pts) > 0:
                        intersection_area = cv2.contourArea(intersection_pts)
                        overlap_ratio = intersection_area / sub_bbox_area
                        
                        if overlap_ratio > best_overlap_ratio:
                            best_overlap_ratio = overlap_ratio
                            best_zone_id = zone["id"]
                
                # Assign detection to zone if overlap exceeds threshold
                if best_zone_id and best_overlap_ratio >= self.occupancy_min_overlap:
                    zone_occupancy[best_zone_id] = True
            
            # Build spot_results from zone_occupancy map
            for zone in self.polygons:
                poly = zone["poly"]
                spot_id = zone["id"]
                is_occupied = zone_occupancy.get(spot_id, False)
                
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
