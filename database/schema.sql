-- raw DDL for PostgreSQL reference

CREATE TYPE connection_type AS ENUM ('fiber', 'edge');
CREATE TYPE device_status AS ENUM ('healthy', 'degraded', 'disconnected', 'error');
CREATE TYPE desired_state AS ENUM ('running', 'stopped', 'maintenance');

CREATE TABLE cameras (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,
    location VARCHAR,
    connection_type connection_type DEFAULT 'fiber',
    stream_url TEXT NOT NULL,
    model_version VARCHAR DEFAULT 'yolo11n',
    processing_interval_sec INTEGER DEFAULT 5,
    geometry JSONB,
    desired_state desired_state DEFAULT 'stopped',
    last_heartbeat TIMESTAMP WITH TIME ZONE,
    last_event_time TIMESTAMP WITH TIME ZONE,
    status device_status DEFAULT 'disconnected',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE occupancy_events (
    id BIGSERIAL PRIMARY KEY,
    camera_id UUID NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    occupied_count INTEGER NOT NULL,
    free_count INTEGER NOT NULL,
    total_slots INTEGER NOT NULL,
    metadata_json JSONB
);

CREATE TABLE health_logs (
    id BIGSERIAL PRIMARY KEY,
    camera_id UUID NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status device_status NOT NULL,
    message TEXT
);

-- Indices for performance
CREATE INDEX idx_occupancy_camera_timestamp ON occupancy_events(camera_id, timestamp);
CREATE INDEX idx_health_camera_timestamp ON health_logs(camera_id, timestamp);
