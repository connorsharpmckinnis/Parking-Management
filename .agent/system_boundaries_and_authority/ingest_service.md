# Ingest Service Authority

The Ingest Service is the gatekeeper between untrusted producers and trusted storage.

## Owns

- Schema validation
- Authentication and authorization
- Rate limiting
- Normalization (e.g., timestamps)
- Write batching or rejection

## Does NOT Own

- Business interpretation
- Policy decisions
- Historical aggregation logic
- Configuration meaning

## Boundary Rule

Even when physically co-located with another service, ingest logic must remain
conceptually isolated and replaceable without semantic changes.
