from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Enum, BigInteger, UUID, Boolean
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import uuid
import enum

Base = declarative_base()

class ConnectionType(enum.Enum):
    FIBER = "fiber" # Centralized processing
    EDGE = "edge"   # Remote processing

class DeviceStatus(enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DISCONNECTED = "disconnected"
    ERROR = "error"

class DesiredState(enum.Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    MAINTENANCE = "maintenance"

class Location(Base):
    __tablename__ = "locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    cameras = relationship("Camera", back_populates="location_ref")
    spots = relationship("Spot", back_populates="location")

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=False)
    
    # Connection details
    connection_type = Column(Enum(ConnectionType), default=ConnectionType.FIBER)
    stream_url = Column(String, nullable=False) # Store encrypted in production
    
    # Vision Config
    model_version = Column(String, default="yolo11n")
    processing_interval_sec = Column(Integer, default=5)
    geometry = Column(JSON, nullable=True) # Polygon zones
    detection_classes = Column(JSON, default=[2, 3, 5, 7]) # COCO classes: car, motorcycle, bus, truck
    
    # State
    desired_state = Column(Enum(DesiredState), default=DesiredState.STOPPED)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
    last_event_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(DeviceStatus), default=DeviceStatus.DISCONNECTED)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    location_ref = relationship("Location", back_populates="cameras")
    events = relationship("OccupancyEvent", back_populates="camera")
    health_logs = relationship("HealthLog", back_populates="camera")
    observations = relationship("SpotObservation", back_populates="camera")

class Spot(Base):
    __tablename__ = "spots"

    id = Column(String, primary_key=True) # e.g. "North-001"
    location_id = Column(UUID(as_uuid=True), ForeignKey("locations.id"), nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    location = relationship("Location", back_populates="spots")
    observations = relationship("SpotObservation", back_populates="spot")

class OccupancyEvent(Base):
    __tablename__ = "occupancy_events"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    camera_id = Column(UUID(as_uuid=True), ForeignKey("cameras.id"), nullable=False)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    occupied_count = Column(Integer, nullable=False)
    free_count = Column(Integer, nullable=False)
    total_slots = Column(Integer, nullable=False)
    
    # Metadata for transparency (Confidence, raw boxes, etc)
    metadata_json = Column(JSON, nullable=True)

    camera = relationship("Camera", back_populates="events")

class SpotObservation(Base):
    __tablename__ = "spot_observations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    spot_id = Column(String, ForeignKey("spots.id"), nullable=False)
    camera_id = Column(UUID(as_uuid=True), ForeignKey("cameras.id"), nullable=False)
    occupied = Column(Boolean, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    spot = relationship("Spot", back_populates="observations")
    camera = relationship("Camera", back_populates="observations")

class HealthLog(Base):
    __tablename__ = "health_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    camera_id = Column(UUID(as_uuid=True), ForeignKey("cameras.id"), nullable=False)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(Enum(DeviceStatus), nullable=False)
    message = Column(String, nullable=True)

    camera = relationship("Camera", back_populates="health_logs")
