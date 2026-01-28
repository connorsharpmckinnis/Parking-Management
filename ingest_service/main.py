"""
Ingest Service: Receives telemetry from Vision Workers and writes to DB.
Separated from Control Plane for scalability (high-frequency writes).
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
import uuid
import os
import sys

# Path hack to access shared database module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db import get_db
from database.models import Camera, OccupancyEvent, HealthLog, Spot, SpotObservation, DeviceStatus

app = FastAPI(title="Telemetry Ingest Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Schemas (duplicated from control_plane for independence) ---

class OccupancyUpdate(BaseModel):
    timestamp: datetime
    occupied_count: int
    free_count: int
    total_slots: int
    metadata_json: Optional[Dict[str, Any]] = None

class HealthUpdate(BaseModel):
    status: DeviceStatus
    message: Optional[str] = None


# --- Endpoints ---

@app.get("/health")
async def health():
    return {"status": "ingest service online"}


@app.post("/cameras/{camera_id}/event")
def camera_event(camera_id: uuid.UUID, update: OccupancyUpdate, db: Session = Depends(get_db)):
    """Receive occupancy event from a Vision Worker and persist to database."""
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # Update camera last event timestamp
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
    
    # Populate spot_observations if camera is linked to a location
    if db_camera.location_id and update.metadata_json and "spot_details" in update.metadata_json:
        valid_spot_ids = {s[0] for s in db.query(Spot.id).filter(Spot.location_id == db_camera.location_id).all()}
        
        for spot in update.metadata_json["spot_details"]:
            s_id = spot["spot_id"]
            prefixed_id = f"{db_camera.location_id}:{s_id}"
            if prefixed_id in valid_spot_ids:
                obs = SpotObservation(
                    spot_id=prefixed_id,
                    camera_id=camera_id,
                    occupied=bool(spot["occupied"]),
                    timestamp=update.timestamp
                )
                db.add(obs)
    
    db.commit()
    return {"received": True}


@app.post("/cameras/{camera_id}/heartbeat")
def camera_heartbeat(camera_id: uuid.UUID, update: HealthUpdate, db: Session = Depends(get_db)):
    """Receive heartbeat from a Vision Worker to indicate liveness."""
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    # Update heartbeat time and status
    from datetime import timezone
    db_camera.last_heartbeat = datetime.now(timezone.utc)
    db_camera.status = update.status
    
    # Log health event
    log = HealthLog(camera_id=camera_id, status=update.status, message=update.message)
    db.add(log)
    db.commit()
    
    return {"status": "ok"}
