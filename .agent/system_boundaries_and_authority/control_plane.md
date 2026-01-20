# Control Plane Authority

The Control Plane is the authoritative source of **system intent and meaning**.

## Owns

- Camera identity and metadata semantics
- Desired operational state
- Configuration meaning and versioning
- Administrative validation rules
- Public API contracts

## Does NOT Own

- Video processing or inference
- Container lifecycle execution
- High-volume buffering or rate control
- Schema enforcement beyond semantic validation

## Database Relationship

- The Control Plane defines *meaning*
- The Database defines *shape and invariants*
- The Control Plane must respect schema, but does not reinterpret it

## Prohibitions

- Do not embed ingest logic beyond request forwarding
- Do not infer system health from telemetry trends
- Do not bypass ingest validation rules
