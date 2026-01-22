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

class VisionWorker:
    def __init__(self):
        # Configuration from Environment Variables
        self.camera_id = os.getenv("CAMERA_ID")
        self.stream_url = os.getenv("STREAM_URL")
        self.api_endpoint = os.getenv("API_ENDPOINT") # http://control-plane:8000
        self.interval = float(os.getenv("POLL_INTERVAL", "5.0"))
        self.model_path = os.getenv("MODEL_PATH", "yolo26x.pt")
        
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

    def _parse_zones(self, zone_json):
        try:
            data = json.loads(zone_json)
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
        model = YOLO(self.model_path)
        
        last_report = 0
        while self.running:
            now = time.time()
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
        # Run inference
        results = model.predict(frame, classes=self.classes, verbose=False)
        occupied_count = 0
        spot_results = []
        
        if results:
            boxes = results[0].boxes
            for zone in self.polygons:
                poly = zone["poly"]
                spot_id = zone["id"]
                is_occupied = False
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    cx, cy = int((x1+x2)/2), int((y1+y2)/2)
                    if cv2.pointPolygonTest(poly, (cx, cy), False) >= 0:
                        is_occupied = True
                        break
                
                spot_results.append({
                    "spot_id": spot_id,
                    "occupied": is_occupied
                })
                
                if is_occupied:
                    occupied_count += 1
            
            # Generate annotated image
            annotated_frame = results[0].plot()
            
            # Draw spot zones
            for zone, res in zip(self.polygons, spot_results):
                poly = zone["poly"]
                # Red if occupied, Green if free
                color = (0, 0, 255) if res["occupied"] else (0, 255, 0)
                cv2.polylines(annotated_frame, [poly], True, color, 2)

            _, buffer = cv2.imencode('.jpg', annotated_frame)
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        else:
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
