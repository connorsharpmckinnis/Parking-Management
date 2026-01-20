---
name: system-boundaries-and-authority
description: Enforces service boundaries, authority, and decision ownership in a distributed system. Use when designing or modifying multi-service architectures.
---

# System Boundaries & Authority

This skill enforces **clear ownership of decisions, data meaning, and behavior** across services.

Architectural boundary violations are considered correctness bugs, even if functionality appears to work.

## Core Principles

1. **Intent has an owner**
2. **Persistence is not decision-making**
3. **Execution does not imply authority**
4. **Co-location does not remove boundaries**
5. **Reconciliation is not interpretation**

When in doubt, prefer explicit boundaries over convenience.

## Authority Model

- **Control Plane**: semantic authority (what things mean, what should happen)
- **Database**: structural authority (what can exist, invariants, integrity)
- **Ingest**: validation and normalization authority
- **Orchestrator**: reconciliation authority
- **Workers**: execution and observation only

## Drift Detection Rule

If logic answers “what should happen?” it likely belongs upstream.
If logic answers “what is happening?” it may belong downstream.
If logic answers both, it is misplaced.

Refer to service-specific documents for constraints.
