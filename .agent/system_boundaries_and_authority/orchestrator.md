# Orchestrator Authority

The Orchestrator reconciles desired state with observed reality.

## Owns

- Reconciliation loops
- Container lifecycle actions
- Drift detection
- Restart and replacement decisions

## Does NOT Own

- Business logic
- Health interpretation beyond observable state
- Configuration semantics
- Telemetry processing

## Database Interaction

- Reads authoritative intent
- Does not write authoritative state
- May emit optional reconciliation metadata if explicitly designed
