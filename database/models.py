from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Enum, BigInteger, UUID
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

class Camera(Base):
    __tablename__ = "cameras"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    location = Column(String, nullable=True)
    
    # Connection details
    connection_type = Column(Enum(ConnectionType), default=ConnectionType.FIBER)
    stream_url = Column(String, nullable=False) # Store encrypted in production
    
    # Vision Config
    model_version = Column(String, default="yolo11n")
    processing_interval_sec = Column(Integer, default=5)
    geometry = Column(JSON, nullable=True) # Polygon zones
    
    # State
    desired_state = Column(Enum(DesiredState), default=DesiredState.STOPPED)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
    last_event_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(DeviceStatus), default=DeviceStatus.DISCONNECTED)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    events = relationship("OccupancyEvent", back_populates="camera")
    health_logs = relationship("HealthLog", back_populates="camera")

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

class HealthLog(Base):
    __tablename__ = "health_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    camera_id = Column(UUID(as_uuid=True), ForeignKey("cameras.id"), nullable=False)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(Enum(DeviceStatus), nullable=False)
    message = Column(String, nullable=True)

    camera = relationship("Camera", back_populates="health_logs")
