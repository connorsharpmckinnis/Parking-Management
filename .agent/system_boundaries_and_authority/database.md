# Database Authority

The Database is the system’s structural memory and integrity enforcer.

## Owns

- Persistence
- Referential integrity
- Concurrency guarantees
- Retention feasibility

## Does NOT Own

- Business meaning
- Decision logic
- Interpretation of stored values

## Schema Evolution Rule

- Existing fields are stable
- New meaning is introduced via new fields
- Application logic must not reinterpret historical schema
