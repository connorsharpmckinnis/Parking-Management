from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import cv2
import numpy as np
import base64

# Path hack for POC
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db import get_db, engine
from database.models import Base, Camera, OccupancyEvent, HealthLog, Location, Spot, SpotObservation, DeviceStatus
from control_plane.schemas import (
    CameraCreate, CameraResponse, CameraUpdate, OccupancyUpdate, 
    HealthUpdate, OccupancyEventResponse, CaptureFrameRequest, CaptureFrameResponse,
    LocationCreate, LocationResponse, SpotResponse
)

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Camera Control Plane")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Parking Management Control Plane Active"}

# --- Locations ---

@app.get("/locations", response_model=List[LocationResponse])
def list_locations(db: Session = Depends(get_db)):
    return db.query(Location).all()

@app.post("/locations", response_model=LocationResponse, status_code=status.HTTP_201_CREATED)
def create_location(location_in: LocationCreate, db: Session = Depends(get_db)):
    db_location = Location(**location_in.model_dump())
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location

@app.get("/locations/{location_id}", response_model=LocationResponse)
def get_location(location_id: uuid.UUID, db: Session = Depends(get_db)):
    db_loc = db.query(Location).filter(Location.id == location_id).first()
    if not db_loc:
        raise HTTPException(status_code=404, detail="Location not found")
    return db_loc

@app.delete("/locations/{location_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_location(location_id: uuid.UUID, db: Session = Depends(get_db)):
    """Delete a location. Note: This will unlink cameras and potentially delete spots."""
    db_location = db.query(Location).filter(Location.id == location_id).first()
    if not db_location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # 1. Unlink cameras (set location_id to null)
    db.query(Camera).filter(Camera.location_id == location_id).update({Camera.location_id: None})
    
    # 2. Delete spots associated with this location
    db.query(SpotObservation).filter(SpotObservation.spot_id.in_(
        db.query(Spot.id).filter(Spot.location_id == location_id)
    )).delete(synchronize_session=False)
    
    db.query(Spot).filter(Spot.location_id == location_id).delete()
    
    # 3. Delete the location
    db.delete(db_location)
    db.commit()
    return None

@app.get("/locations/{location_id}/status")
def get_location_status(location_id: uuid.UUID, db: Session = Depends(get_db)):
    """Return the latest occupancy status for all spots in a location."""
    spots = db.query(Spot).filter(Spot.location_id == location_id).all()
    
    results = []
    for spot in spots:
        # Get latest observation for this spot
        latest_obs = db.query(SpotObservation).filter(SpotObservation.spot_id == spot.id).order_by(SpotObservation.timestamp.desc()).first()
        results.append({
            "spot_id": spot.id,
            "name": spot.name,
            "occupied": latest_obs.occupied if latest_obs else False,
            "last_update": latest_obs.timestamp if latest_obs else None
        })
    
    return results

# --- Cameras ---

@app.get("/cameras", response_model=List[CameraResponse])
def list_cameras(db: Session = Depends(get_db)):
    cameras = db.query(Camera).all()
    for cam in cameras:
        cam.status = _compute_status(cam)
    return cameras

@app.get("/events")
def list_events(camera_id: Optional[uuid.UUID] = None, limit: int = 100, db: Session = Depends(get_db)):
    """Get recent occupancy events with camera name and location."""
    query = db.query(
        OccupancyEvent,
        Camera.name.label('camera_name'),
        Location.name.label('location_name')
    ).join(Camera, OccupancyEvent.camera_id == Camera.id)\
     .join(Location, Camera.location_id == Location.id)
    
    if camera_id:
        query = query.filter(OccupancyEvent.camera_id == camera_id)
    
    results = query.order_by(OccupancyEvent.timestamp.desc()).limit(limit).all()
    
    # Transform results to include camera details
    return [
        {
            "id": row.OccupancyEvent.id,
            "camera_id": row.OccupancyEvent.camera_id,
            "camera_name": row.camera_name,
            "location_name": row.location_name,
            "timestamp": row.OccupancyEvent.timestamp,
            "occupied_count": row.OccupancyEvent.occupied_count,
            "free_count": row.OccupancyEvent.free_count,
            "total_slots": row.OccupancyEvent.total_slots,
            "metadata_json": row.OccupancyEvent.metadata_json
        }
        for row in results
    ]

def _sync_spots(db: Session, db_camera: Camera):
    """Ensure all spots defined in camera geometry are registered in the spots table."""
    if not db_camera.location_id or not db_camera.geometry or not isinstance(db_camera.geometry, list):
        return
    
    seen_ids = set()
    for zone in db_camera.geometry:
        if not isinstance(zone, dict):
            continue
        spot_id = zone.get("id")
        if not spot_id or spot_id in seen_ids:
            continue
        
        seen_ids.add(spot_id)
        
        # Internal UUID for unique identification across locations
        prefixed_id = f"{db_camera.location_id}:{spot_id}"
            
        # Check if spot exists
        db_spot = db.query(Spot).filter(Spot.id == prefixed_id).first()
        if not db_spot:
            db_spot = Spot(
                id=prefixed_id,
                location_id=db_camera.location_id,
                name=spot_id # User facing name
            )
            db.add(db_spot)
        else:
            # Ensure it's linked to the correct location (re-parenting if moved)
            db_spot.location_id = db_camera.location_id
    db.commit()

@app.post("/cameras", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
def create_camera(camera_in: CameraCreate, db: Session = Depends(get_db)):
    db_camera = Camera(**camera_in.model_dump())
    db.add(db_camera)
    db.commit()
    db.refresh(db_camera)
    
    # Compute status for immediate response
    db_camera.status = _compute_status(db_camera)
    
    _sync_spots(db, db_camera)
    
    return db_camera

# NOTE: /cameras/{camera_id}/heartbeat and /cameras/{camera_id}/event
# have been moved to the Ingest Service for scalability.
# Vision Workers now POST to http://ingest-service:8001/cameras/{id}/event

def _compute_status(camera: Camera) -> DeviceStatus:
    """Determine status based on heartbeat recency."""
    if not camera.last_heartbeat:
        return DeviceStatus.DISCONNECTED
        
    delta = (datetime.now(timezone.utc) - camera.last_heartbeat).total_seconds()
    
    # Relaxed thresholds to accommodate default 60s polling intervals
    if delta > 600: # 10 minutes without heartbeat
        return DeviceStatus.DISCONNECTED
    elif delta > 300: # 5 minutes without heartbeat
        return DeviceStatus.DEGRADED
        
    return camera.status # Return reported status (usually HEALTHY)

@app.get("/cameras/{camera_id}", response_model=CameraResponse)
def get_camera(camera_id: uuid.UUID, db: Session = Depends(get_db)):
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
        
    # Dynamically update status for response (read-only)
    # Note: We don't commit this to DB on read to avoid locking, 
    # but the frontend will see the computed status.
    db_camera.status = _compute_status(db_camera)
    
    return db_camera

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
    
    # Sync spots if location_id or geometry was updated
    if "location_id" in update_data or "geometry" in update_data:
        _sync_spots(db, db_camera)
        
    return db_camera

@app.delete("/cameras/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_camera(camera_id: uuid.UUID, db: Session = Depends(get_db)):
    """Permanently delete a camera and its related data."""
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    location_id = db_camera.location_id

    # 1. Delete transient data
    db.query(OccupancyEvent).filter(OccupancyEvent.camera_id == camera_id).delete()
    db.query(HealthLog).filter(HealthLog.camera_id == camera_id).delete()
    db.query(SpotObservation).filter(SpotObservation.camera_id == camera_id).delete()
    
    # 2. Identify spots that were uniquely referenced by THIS camera in this location
    if location_id and db_camera.geometry:
        # Get all spots currently in this location
        all_spots = db.query(Spot).filter(Spot.location_id == location_id).all()
        
        # Get all OTHER cameras in this location
        other_cameras = db.query(Camera).filter(Camera.location_id == location_id, Camera.id != camera_id).all()
        
        # Build set of spot IDs covered by OTHER cameras
        covered_by_others = set()
        for oc in other_cameras:
            if oc.geometry:
                for zone in oc.geometry:
                    covered_by_others.add(f"{location_id}:{zone.get('id')}")
        
        # If a spot isn't covered by others, we can safely prune it (or leave it if you want history)
        # For PeakPark, let's prune orphaned spots to keep the UI clean as requested.
        for spot in all_spots:
            if spot.id not in covered_by_others:
                db.query(SpotObservation).filter(SpotObservation.spot_id == spot.id).delete()
                db.delete(spot)

    db.delete(db_camera)
    db.commit()
    return None

@app.delete("/spots/{spot_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_spot(spot_id: str, db: Session = Depends(get_db)):
    """Manually delete a spot and its history."""
    db_spot = db.query(Spot).filter(Spot.id == spot_id).first()
    if not db_spot:
        raise HTTPException(status_code=404, detail="Spot not found")
    
    db.query(SpotObservation).filter(SpotObservation.spot_id == spot_id).delete()
    db.delete(db_spot)
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

@app.get("/cameras/{camera_id}/snapshot", response_model=CaptureFrameResponse)
def get_camera_snapshot(camera_id: uuid.UUID, annotate: bool = True, db: Session = Depends(get_db)):
    """Fetch a live frame from the camera and optionally annotate it with spot zones."""
    db_camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    try:
        cap = cv2.VideoCapture(db_camera.stream_url)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Could not open stream")
        
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            raise HTTPException(status_code=400, detail="Failed to read frame from stream")
        
        if annotate and db_camera.geometry:
            for zone in db_camera.geometry:
                points = np.array(zone['points'], np.int32)
                # Draw polygon
                cv2.polylines(frame, [points], True, (0, 255, 0), 2)
                
                # Draw ID in center
                if 'id' in zone:
                    M = cv2.moments(points)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                    else:
                        # Fallback to mean if moments fail
                        cx, cy = np.mean(points, axis=0).astype(int)
                    
                    text = str(zone['id'])
                    # Simple text with background for readability
                    font = cv2.FONT_HERSHEY_SIMPLEX
                    scale = 0.5
                    thickness = 1
                    (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
                    cv2.rectangle(frame, (cx - tw//2 - 2, cy - th//2 - 2), (cx + tw//2 + 2, cy + th//2 + 2), (0, 0, 0), -1)
                    cv2.putText(frame, text, (cx - tw//2, cy + th//2), font, scale, (255, 255, 255), thickness)

        height, width = frame.shape[:2]
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return CaptureFrameResponse(
            image_base64=image_base64,
            width=width,
            height=height
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Snapshot error: {str(e)}")

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Aggregate statistics for the dashboard."""
    total_cameras = db.query(Camera).count()
    active_cameras = db.query(Camera).filter(Camera.status == DeviceStatus.HEALTHY).count()
    total_locations = db.query(Location).count()
    
    # Spot stats
    # We need the LATEST observation for every spot
    # This is slightly expensive, so we might want to optimize with a materialized view later
    # For now, we fetch all latest observations
    
    # Subquery to get max timestamp per spot
    subquery = db.query(
        SpotObservation.spot_id,
        func.max(SpotObservation.timestamp).label('max_ts')
    ).group_by(SpotObservation.spot_id).subquery()
    
    # Join to get the status
    latest_obs = db.query(SpotObservation).join(
        subquery,
        (SpotObservation.spot_id == subquery.c.spot_id) & 
        (SpotObservation.timestamp == subquery.c.max_ts)
    ).all()
    
    occupied_count = sum(1 for obs in latest_obs if obs.occupied)
    
    # Total spots (all configured spots)
    total_spots = db.query(Spot).count()
    
    # Recent events count (last 24h)
    one_day_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
    # Note: timestamps in DB might be naive or aware depending on driver. 
    # Assuming naive UTC for sqlite/postgres usually implies simple comparison.
    # If using postgres with timestamptz, ensure comp.
    recent_events = db.query(OccupancyEvent).filter(OccupancyEvent.timestamp >= one_day_ago).count()
    
    return {
        "total_cameras": total_cameras,
        "active_cameras": active_cameras,
        "total_locations": total_locations,
        "total_spots": total_spots,
        "occupied_spots": occupied_count,
        "recent_events_24h": recent_events
    }

# --- Analytics & Reporting ---

@app.get("/spots")
def list_spots(location_id: Optional[uuid.UUID] = None, db: Session = Depends(get_db)):
    """Return all spots with their latest status and location name."""
    query = db.query(
        Spot,
        Location.name.label('location_name')
    ).join(Location, Spot.location_id == Location.id)
    
    if location_id:
        query = query.filter(Spot.location_id == location_id)
        
    spots_data = query.all()
    results = []
    
    for row in spots_data:
        spot = row.Spot
        # Get latest observation
        latest = db.query(SpotObservation)\
            .filter(SpotObservation.spot_id == spot.id)\
            .order_by(SpotObservation.timestamp.desc())\
            .first()
            
        results.append({
            "id": spot.id,
            "name": spot.name,
            "location_id": spot.location_id,
            "location_name": row.location_name,
            "occupied": latest.occupied if latest else False,
            "last_update": latest.timestamp if latest else None
        })
        
    return results

@app.get("/spots/{spot_id}/history")
def get_spot_history_endpoint(spot_id: str, limit: int = 50, db: Session = Depends(get_db)):
    """Get recent status changes for a specific spot."""
    history = db.query(SpotObservation)\
        .filter(SpotObservation.spot_id == spot_id)\
        .order_by(SpotObservation.timestamp.desc())\
        .limit(limit)\
        .all()
        
    return [
        {
            "timestamp": obs.timestamp,
            "occupied": obs.occupied,
            "camera_id": obs.camera_id
        }
        for obs in history
    ]

# --- Data Export (Power BI / CSV) ---

from fastapi.responses import StreamingResponse
import csv
import io

@app.get("/analytics/observations")
def export_observations(
    location_id: Optional[uuid.UUID] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    format: str = "csv",
    db: Session = Depends(get_db)
):
    """
    Export spot observations with location and spot names for Power BI.
    
    Parameters:
    - location_id: Optional filter to a specific location.
    - start_date: Optional start of time range (ISO format).
    - end_date: Optional end of time range (ISO format).
    - format: 'csv' (default) or 'json'.
    """
    query = db.query(
        SpotObservation.id,
        SpotObservation.timestamp,
        SpotObservation.occupied,
        SpotObservation.spot_id,
        Spot.name.label('spot_name'),
        Spot.location_id,
        Location.name.label('location_name'),
        SpotObservation.camera_id,
        Camera.name.label('camera_name')
    ).join(Spot, SpotObservation.spot_id == Spot.id)\
     .join(Location, Spot.location_id == Location.id)\
     .join(Camera, SpotObservation.camera_id == Camera.id)
    
    if location_id:
        query = query.filter(Spot.location_id == location_id)
    if start_date:
        query = query.filter(SpotObservation.timestamp >= start_date)
    if end_date:
        query = query.filter(SpotObservation.timestamp <= end_date)
    
    query = query.order_by(SpotObservation.timestamp.desc())
    
    # Limit to prevent huge exports (can be adjusted)
    results = query.limit(100000).all()
    
    if format == "json":
        return [
            {
                "id": row.id,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                "occupied": row.occupied,
                "spot_id": row.spot_id,
                "spot_name": row.spot_name,
                "location_id": str(row.location_id),
                "location_name": row.location_name,
                "camera_id": str(row.camera_id),
                "camera_name": row.camera_name
            }
            for row in results
        ]
    
    # CSV format
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "timestamp", "occupied", "spot_id", "spot_name", "location_id", "location_name", "camera_id", "camera_name"])
    
    for row in results:
        writer.writerow([
            row.id,
            row.timestamp.isoformat() if row.timestamp else "",
            row.occupied,
            row.spot_id,
            row.spot_name,
            str(row.location_id),
            row.location_name,
            str(row.camera_id),
            row.camera_name
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=observations_export.csv"}
    )


@app.get("/analytics/health")
def export_health_history(
    camera_id: Optional[uuid.UUID] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    format: str = "csv",
    db: Session = Depends(get_db)
):
    """
    Export camera health history for uptime analysis.
    
    Parameters:
    - camera_id: Optional filter to a specific camera.
    - start_date: Optional start of time range.
    - end_date: Optional end of time range.
    - format: 'csv' (default) or 'json'.
    """
    query = db.query(
        HealthLog.id,
        HealthLog.timestamp,
        HealthLog.status,
        HealthLog.message,
        HealthLog.camera_id,
        Camera.name.label('camera_name'),
        Location.name.label('location_name')
    ).join(Camera, HealthLog.camera_id == Camera.id)\
     .outerjoin(Location, Camera.location_id == Location.id)
    
    if camera_id:
        query = query.filter(HealthLog.camera_id == camera_id)
    if start_date:
        query = query.filter(HealthLog.timestamp >= start_date)
    if end_date:
        query = query.filter(HealthLog.timestamp <= end_date)
    
    query = query.order_by(HealthLog.timestamp.desc())
    results = query.limit(50000).all()
    
    if format == "json":
        return [
            {
                "id": row.id,
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                "status": row.status.value if row.status else None,
                "message": row.message,
                "camera_id": str(row.camera_id),
                "camera_name": row.camera_name,
                "location_name": row.location_name
            }
            for row in results
        ]
    
    # CSV format
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "timestamp", "status", "message", "camera_id", "camera_name", "location_name"])
    
    for row in results:
        writer.writerow([
            row.id,
            row.timestamp.isoformat() if row.timestamp else "",
            row.status.value if row.status else "",
            row.message or "",
            str(row.camera_id),
            row.camera_name,
            row.location_name or ""
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=health_export.csv"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
