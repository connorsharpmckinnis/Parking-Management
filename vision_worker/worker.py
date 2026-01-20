import cv2
import time
import os
import json
import requests
import threading
from datetime import datetime, timezone
from ultralytics import YOLO
import numpy as np

class VisionWorker:
    def __init__(self):
        # Configuration from Environment Variables
        self.camera_id = os.getenv("CAMERA_ID")
        self.stream_url = os.getenv("STREAM_URL")
        self.api_endpoint = os.getenv("API_ENDPOINT") # http://control-plane:8000
        self.interval = float(os.getenv("POLL_INTERVAL", "5.0"))
        self.model_path = os.getenv("MODEL_PATH", "yolo11n.pt")
        
        # Geometry parsing
        zone_json = os.getenv("ZONE_CONFIG", "[]")
        self.polygons = self._parse_zones(zone_json)
        self.total_slots = len(self.polygons)
        
        self.running = False
        self.latest_frame = None
        self.lock = threading.Lock()

    def _parse_zones(self, zone_json):
        try:
            data = json.loads(zone_json)
            polys = []
            for item in data:
                pts = np.array(item["points"], np.int32).reshape((-1, 1, 2))
                polys.append(pts)
            return polys
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
        results = model.predict(frame, classes=[2, 3, 5, 7], verbose=False)
        occupied = 0
        
        if results:
            boxes = results[0].boxes
            for poly in self.polygons:
                is_occupied = False
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    cx, cy = int((x1+x2)/2), int((y1+y2)/2)
                    if cv2.pointPolygonTest(poly, (cx, cy), False) >= 0:
                        is_occupied = True
                        break
                if is_occupied:
                    occupied += 1

        # POST Telemetry
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "occupied_count": occupied,
            "free_count": self.total_slots - occupied,
            "total_slots": self.total_slots
        }
        
        try:
            url = f"{self.api_endpoint}/cameras/{self.camera_id}/event"
            requests.post(url, json=payload, timeout=5)
            print(f"Reported: {occupied}/{self.total_slots}")
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
