# Orchestrator Service

## 🎼 Role
The "Reconciler". A background background process that ensures reality (running containers) matches the database's intent.

## 📋 Responsibilities
1.  **Reconciliation Loop**: Polls the Control Plane every 30 seconds for desired camera states.
2.  **GPU Management**: Detects host NVIDIA capabilities and automatically applies `--runtime nvidia` and `--ipc host` to workers.
3.  **Dynamic Configuration**: Orchestrates the deployment of `vision_worker` containers with the correct environment variables (`INGEST_URL`, `CONFIG_URL`, etc.).
4.  **Lifecycle Control**: 
    -   **Start**: Launches a new container if intent is `running`.
    -   **Stop**: Removes container if intent is `stopped`.
    -   **Sync**: Restarts workers if their internal stream or geometry config changes in the database.

## 🛠 Tech Stack
-   **Language**: Python 3.11+
-   **Runtime**: Docker (accessed via `/var/run/docker.sock`)
-   **Automation**: Uses `subprocess` to execute Docker CLI commands for maximum compatibility with NVIDIA runtimes.

## 🚀 GPU Logic
The Orchestrator checks for the presence of `nvidia-smi` on the host. If found:
- It injects `--runtime nvidia` into the `docker run` command.
- It sets `--ipc host` to improve YOLO inference performance.
- It passes `NVIDIA_VISIBLE_DEVICES=all`.

## 🧪 Scenarios & Requirements

### Scenario A: GPU vs CPU Mode
**Requirement**: Graceful fallback.
1.  Orchestrator runs `nvidia-smi`.
2.  If successful, workers are started with GPU flags.
3.  If it fails, workers are started in CPU-only mode (using `ultralytics` CPU code as fallback).

### Scenario B: Mass Update
**Requirement**: Configuration consistency.
1.  Admin changes the global `INGEST_URL`.
2.  Orchestrator detects that running workers have an old `INGEST_URL` in their environment.
3.  Orchestrator cycles through all workers, restarting them with the new endpoint.
