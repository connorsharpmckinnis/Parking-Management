from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID
from typing import Optional, Dict, Any, List, Union
from database.models import ConnectionType, DesiredState, DeviceStatus

class LocationBase(BaseModel):
    name: str

class LocationCreate(LocationBase):
    pass

class LocationResponse(LocationBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

class SpotBase(BaseModel):
    id: str
    location_id: UUID
    name: Optional[str] = None

class SpotResponse(SpotBase):
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime

class CameraBase(BaseModel):
    name: str
    location_id: UUID
    connection_type: ConnectionType = ConnectionType.FIBER
    stream_url: str
    model_version: str = "yolo11n"
    processing_interval_sec: int = 5
    geometry: Optional[Any] = None
    detection_classes: List[int] = [2, 3, 5, 7]  # COCO classes
    desired_state: DesiredState = DesiredState.STOPPED

class CameraCreate(CameraBase):
    pass

class CameraUpdate(BaseModel):
    """Schema for partial camera updates (PATCH)."""
    name: Optional[str] = None
    location_id: Optional[UUID] = None
    desired_state: Optional[DesiredState] = None
    geometry: Optional[Any] = None
    processing_interval_sec: Optional[int] = None

class CameraResponse(CameraBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    status: DeviceStatus
    last_heartbeat: Optional[datetime] = None
    last_event_time: Optional[datetime] = None
    created_at: datetime

class OccupancyUpdate(BaseModel):
    timestamp: datetime
    occupied_count: int
    free_count: int
    total_slots: int
    metadata_json: Optional[Dict[str, Any]] = None

class HealthUpdate(BaseModel):
    status: DeviceStatus
    message: Optional[str] = None

class OccupancyEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    camera_id: UUID
    timestamp: datetime
    occupied_count: int
    free_count: int
    total_slots: int
    metadata_json: Optional[Dict[str, Any]] = None

class CaptureFrameRequest(BaseModel):
    stream_url: str

class CaptureFrameResponse(BaseModel):
    image_base64: str
    width: int
    height: int
