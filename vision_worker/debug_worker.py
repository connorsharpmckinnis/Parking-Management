import cv2
import os
import json
import time
from ultralytics import YOLO
import numpy as np
import sys

# Add parent directory to path to import VisionWorker
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from worker import VisionWorker

class DebugWorker(VisionWorker):
    def __init__(self, stream_url=None, zones=None, classes=None):
        # Override env vars for local testing if provided
        if stream_url: os.environ["STREAM_URL"] = stream_url
        if zones: os.environ["ZONE_CONFIG"] = json.dumps(zones)
        if classes: os.environ["DETECTION_CLASSES"] = json.dumps(classes)
        
        # Set dummy api endpoint for safety
        os.environ["API_ENDPOINT"] = "http://localhost:8000"
        os.environ["CAMERA_ID"] = "debug-camera"
        
        super().__init__()
        self.report_annotated = True

    def _process_loop(self):
        print("DEBUG MODE: Press 'q' in the window to quit.")
        model = YOLO(self.model_path)
        
        while self.running:
            with self.lock:
                frame = self.latest_frame.copy() if self.latest_frame is not None else None
            
            if frame is not None:
                # We reuse the logic but show the frame locally
                self._analyze_and_report(model, frame)
                
                # Show frame
                cv2.imshow("Vision Worker Debug", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.running = False
                    break
            else:
                print("Waiting for frame...")
                time.sleep(1)

    def _analyze_and_report(self, model, frame):
        # We call the parent logic to ensure we are testing the actual prod code
        # But we don't necessarily want to send data to the backend during local debug
        super()._analyze_and_report(model, frame)
        # The parent already annotated the frame because self.report_annotated = True

if __name__ == "__main__":
    # Example usage:
    # python debug_worker.py "http://user:pass@ip/stream" '[{"id":"spot1","points":[[...]]}]'
    stream = sys.argv[1] if len(sys.argv) > 1 else None
    zones_str = sys.argv[2] if len(sys.argv) > 2 else "[]"
    print(f"RAW zones_str: {repr(zones_str)}")
    
    if not stream:
        print("Usage: python debug_worker.py <STREAM_URL> [ZONE_CONFIG_JSON]")
        sys.exit(1)
        
    worker = DebugWorker(stream_url=stream, zones=json.loads(zones_str))
    worker.start()
