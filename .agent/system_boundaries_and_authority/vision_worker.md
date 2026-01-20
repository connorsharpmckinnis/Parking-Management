# Vision Worker Doctrine

The Vision Worker is intentionally dumb, stateless, and replaceable.

## Owns

- Single-stream connectivity
- Frame-level inference
- Mechanical aggregation (e.g., averages, counts)
- Raw observation reporting
- Local retry mechanics

## Does NOT Own

- Business rules or thresholds
- Cross-camera context
- Historical interpretation
- Configuration decisions
- Persistent state

## Retry Policy

- Retry behavior may be centrally configured
- Retry mechanics are locally implemented
- Workers must not invent retry semantics

## Reporting Rules

- Report observations, not conclusions
- Confidence is a measurement, not a judgment
- Silence or failure is preferable to fabricated certainty
