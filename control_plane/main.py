from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import cv2
import base64

# Path hack for POC
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db import get_db, engine
from database.models import Base, Camera, OccupancyEvent, HealthLog
from control_plane.schemas import (
    CameraCreate, CameraResponse, CameraUpdate, OccupancyUpdate, 
    HealthUpdate, OccupancyEventResponse, CaptureFrameRequest, CaptureFrameResponse
)

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Camera Control Plane")

@app.get("/")
async def root():
    return {"message": "Parking Management Control Plane Active"}

@app.get("/cameras", response_model=List[CameraResponse])
def list_cameras(db: Session = Depends(get_db)):
    return db.query(Camera).all()

@app.get("/events", response_model=List[OccupancyEventResponse])
def list_events(camera_id: Optional[uuid.UUID] = None, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(OccupancyEvent)
    if camera_id:
        query = query.filter(OccupancyEvent.camera_id == camera_id)
    return query.order_by(OccupancyEvent.timestamp.desc()).limit(limit).all()

@app.post("/cameras", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
def create_camera(camera_in: CameraCreate, db: Session = Depends(get_db)):
    db_camera = Camera(**camera_in.model_dump())
    db.add(db_camera)
    db.commit()
    db.refresh(db_camera)
    return db_camera

@app.get("/cameras/{camera_id}", response_model=CameraResponse)
def get_camera(camera_id: uuid.UUID, db: Session = Depends(get_db)):
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return db_camera

@app.post("/cameras/{camera_id}/heartbeat")
def camera_heartbeat(camera_id: uuid.UUID, update: HealthUpdate, db: Session = Depends(get_db)):
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # Update camera status
    db_camera.status = update.status
    db_camera.last_heartbeat = datetime.now(timezone.utc)
    
    # Log health event
    log = HealthLog(camera_id=camera_id, status=update.status, message=update.message)
    db.add(log)
    db.commit()
    return {"status": "ok"}

@app.post("/cameras/{camera_id}/event")
def camera_event(camera_id: uuid.UUID, update: OccupancyUpdate, db: Session = Depends(get_db)):
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # Update camera last event
    db_camera.last_event_time = update.timestamp
    
    # Create event record
    event = OccupancyEvent(
        camera_id=camera_id,
        timestamp=update.timestamp,
        occupied_count=update.occupied_count,
        free_count=update.free_count,
        total_slots=update.total_slots,
        metadata_json=update.metadata_json
    )
    db.add(event)
    db.commit()
    return {"received": True}

@app.patch("/cameras/{camera_id}", response_model=CameraResponse)
def update_camera(camera_id: uuid.UUID, camera_update: CameraUpdate, db: Session = Depends(get_db)):
    """Update camera settings or desired_state (start/stop)."""
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    update_data = camera_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_camera, key, value)
    
    db.commit()
    db.refresh(db_camera)
    return db_camera

@app.delete("/cameras/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_camera(camera_id: uuid.UUID, db: Session = Depends(get_db)):
    """Permanently delete a camera and its related data."""
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # Delete related events and logs first (or rely on CASCADE if set up)
    db.query(OccupancyEvent).filter(OccupancyEvent.camera_id == camera_id).delete()
    db.query(HealthLog).filter(HealthLog.camera_id == camera_id).delete()
    
    db.delete(db_camera)
    db.commit()
    return None

@app.post("/cameras/capture-frame", response_model=CaptureFrameResponse)
def capture_frame_endpoint(request: CaptureFrameRequest):
    """Capture a single frame from an RTSP/HTTP stream and return as base64."""
    try:
        cap = cv2.VideoCapture(request.stream_url)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Could not open stream")
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise HTTPException(status_code=400, detail="Failed to read frame from stream")
        
        height, width = frame.shape[:2]
        
        # Encode as JPEG
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return CaptureFrameResponse(
            image_base64=image_base64,
            width=width,
            height=height
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Frame capture error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
