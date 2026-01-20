# Orchestrator Service

## 🎼 Role
The "Reconciler". A background process that ensures reality matches the database's intent. It is the "Operator" pattern applied to our simple Docker/Podman setup.

## 📋 Responsibilities
1.  **Reconciliation Loop**: Runs every ~30 seconds.
2.  **Comparison**:
    -   Fetch `desired_state` of all cameras from DB/Control Plane.
    -   Fetch `actual_state` of running containers (via Docker Socket/Podman API).
3.  **Action**:
    -   **Start**: If DB says "Running" but no container exists -> Launch `vision_worker` container.
    -   **Stop**: If DB says "Stopped" but container exists -> Kill container.
    -   **Restart**: If container is "Unhealthy" or "Exited" -> Restart it.
    -   **Update**: If DB config changed (new polygons) -> Restart container with new Env Vars.

## 🛠 Tech Stack
-   **Language**: Python 3.11+
-   **Container runtime**: Podman (preferred) or Docker.
-   **Library**: `python-on-whales` or `podman-py`.

## 🧪 Scenarios & Requirements

### Scenario A: Server Reboot
**Requirement**: System auto-recovery.
1.  Server restarts. No containers are running.
2.  Orchestrator starts (via systemd).
3.  Orchestrator sees 50 cameras marked "Running" in DB.
4.  Orchestrator launches 50 `vision_worker` containers sequentially.

### Scenario B: Configuration Change
**Requirement**: Zero-touch updates.
1.  Admin updates the parking zones for Camera X in the Control Plane UI.
2.  Control Plane updates `cameras` table and bumps a `config_version`.
3.  Orchestrator detects mismatch (Container Env Var `CONFIG_VER=1` vs DB `CONFIG_VER=2`).
4.  Orchestrator stops old container, starts new one with updated zones.

### Scenario C: Rogue Container
**Requirement**: Cleanliness.
1.  An admin manually started a test container `worker-test-123`.
2.  Orchestrator sees this container is NOT in the database.
3.  Orchestrator stops and removes the rogue container to free resources.
