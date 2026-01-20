import cv2
import time
import threading
import json
import numpy as np
import db
from ultralytics import YOLO

class ParkingMonitor:
    def __init__(self, stream_url, model_path="yolo11n.pt", json_path="bounding_boxes.json", interval=5):
        self.stream_url = stream_url
        self.model_path = model_path
        self.json_path = json_path
        self.interval = interval
        self.running = False
        
        # Threads
        self.cap_thread = None
        self.proc_thread = None
        
        # State
        self.latest_frame = None
        self.lock = threading.Lock()
        
        # Analysis Data
        self.occupied_count = 0
        self.free_count = 0
        self.total_slots = 0
        self.last_check_time = 0
        self.polygons = []
        
        # Load polygons
        self.load_polygons()

    def load_polygons(self):
        try:
            with open(self.json_path, 'r') as f:
                data = json.load(f)
                # Parse points into numpy arrays for cv2
                self.polygons = []
                for item in data:
                    pts = np.array(item["points"], np.int32)
                    pts = pts.reshape((-1, 1, 2))
                    self.polygons.append(pts)
                self.total_slots = len(self.polygons)
        except Exception as e:
            print(f"Error loading polygons: {e}")

    def start(self):
        if self.running:
            return
        
        self.running = True
        
        # Start capture thread
        self.cap_thread = threading.Thread(target=self._capture_loop)
        self.cap_thread.daemon = True
        self.cap_thread.start()
        
        # Start processing thread
        self.proc_thread = threading.Thread(target=self._process_loop)
        self.proc_thread.daemon = True
        self.proc_thread.start()
        
        print("Parking Monitor started.")

    def stop(self):
        self.running = False
        if self.cap_thread:
            self.cap_thread.join(timeout=1)
        if self.proc_thread:
            self.proc_thread.join(timeout=1)
        print("Parking Monitor stopped.")

    def _capture_loop(self):
        cap = cv2.VideoCapture(self.stream_url)
        # Attempt to reduce buffer size to ensure real-time frames
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        while self.running:
            ret, frame = cap.read()
            if not ret:
                print("Stream disconnected. Reconnecting in 2s...")
                time.sleep(2)
                cap.release()
                cap = cv2.VideoCapture(self.stream_url)
                continue
            
            with self.lock:
                self.latest_frame = frame
                
            # Sleep slightly to save CPU if FPS is high? 
            # Actually, standard blocking read is fine.
            # But let's not busy wait if camera is slow.
            time.sleep(0.01)
            
        cap.release()

    def _process_loop(self):
        print("Loading YOLO model...")
        try:
            model = YOLO(self.model_path)
        except Exception as e:
            print(f"Failed to load model: {e}")
            self.running = False
            return

        while self.running:
            now = time.time()
            time_since = now - self.last_check_time
            
            if time_since >= self.interval:
                # Time to check!
                with self.lock:
                    if self.latest_frame is None:
                        time.sleep(1)
                        continue
                    # Copy frame to avoid blocking capture
                    frame_to_process = self.latest_frame.copy()
                
                self._analyze_frame(model, frame_to_process)
                self.last_check_time = time.time()
            
            time.sleep(1) # Check schedule every second

    def _analyze_frame(self, model, frame):
        try:
            # Classes: 2=car, 3=motorcycle, 5=bus, 7=truck (COCO indices)
            results = model.predict(frame, classes=[2, 3, 5, 7], verbose=False)
            
            occupied = 0
            
            if results and len(results) > 0:
                result = results[0]
                boxes = result.boxes
                
                # Check each polygon
                for poly in self.polygons:
                    is_occupied = False
                    for box in boxes:
                        # Get center of box
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        cx = int((x1 + x2) / 2)
                        cy = int((y1 + y2) / 2)
                        
                        # Point in Polygon
                        # returns +1 if inside, -1 if outside, 0 if on edge
                        dist = cv2.pointPolygonTest(poly, (cx, cy), False)
                        if dist >= 0:
                            is_occupied = True
                            break
                    
                    if is_occupied:
                        occupied += 1
            
            free = self.total_slots - occupied
            self.occupied_count = occupied
            self.free_count = free
            
            # Save to DB
            db.log_data(occupied, free)
            
        except Exception as e:
            print(f"Analysis error: {e}")

    def get_frame(self):
        with self.lock:
            if self.latest_frame is None:
                return None
            
            # Annotate frame with overlay
            # We clone it so we don't mess up the raw capture (though it's overwritten anyway)
            display_frame = self.latest_frame.copy()
        
        # Add overlay info
        h, w = display_frame.shape[:2]
        time_to_next = max(0, int(self.interval - (time.time() - self.last_check_time)))
        
        # Draw status box
        cv2.rectangle(display_frame, (10, 10), (300, 110), (0, 0, 0), -1)
        cv2.rectangle(display_frame, (10, 10), (300, 110), (255, 255, 255), 1)
        
        cv2.putText(display_frame, f"Occupied: {self.occupied_count}/{self.total_slots}", (20, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        if time_to_next > 0:
             cv2.putText(display_frame, f"Next Scan: {time_to_next}s", (20, 80), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        else:
             cv2.putText(display_frame, "Scanning...", (20, 80), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

        # Draw Polygons (Optional: Make them green/red based on state?)
        # Since we don't track state per/polygon in variables permanently, 
        # we only know the total counts in this simplified version.
        # To draw them Red/Green, we need to return the status of each polygon from _analyze_frame.
        # But for now, user asked for "Live feed from camera", so just drawing the outlines is good enough 
        # to see where they are.
        cv2.polylines(display_frame, self.polygons, True, (255, 255, 0), 2)

        ret, buffer = cv2.imencode('.jpg', display_frame)
        return buffer.tobytes()
