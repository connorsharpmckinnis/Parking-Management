---
description: Build, push, and deploy Docker images to production
---

# Docker Production Deployment Workflow

This workflow covers the complete dev-to-production cycle for the Parking Management system.

## Prerequisites

1. **Docker Desktop** running locally
2. **DockerHub account** with repository access
3. **Logged into DockerHub**: `docker login`
4. **Production server** with Docker and Docker Compose installed

---

## One-Time Setup

### 1. Configure Your DockerHub Username

Edit these files and replace `YOUR_DOCKERHUB_USERNAME` with your actual username:

- `compose.prod.yaml`
- `build-and-push.ps1`

Or run the script with the parameter:
```powershell
.\build-and-push.ps1 -DockerHubUsername yourusername
```

### 2. Create DockerHub Repositories (Optional)

DockerHub will auto-create repositories on first push, but you can pre-create them for better organization:

- `yourusername/parking-control-plane`
- `yourusername/parking-ingest-service`
- `yourusername/parking-dashboard`
- `yourusername/parking-orchestrator`
- `yourusername/parking-vision-worker`
- `yourusername/parking-mqtt-broker`
- `yourusername/parking-edge-simulator`
- `yourusername/parking-ingest-bridge`

---

## Development Workflow

### Local Development (Using compose.yaml)

The original `compose.yaml` is your **development** compose file with:
- Local builds from source
- Mounted code volumes for hot-reload
- Useful during active development

```powershell
# Start development environment
docker compose up --build -d

# View logs
docker compose logs -f

# Tear down
docker compose down
```

---

## Production Deployment Workflow

### Step 1: Build and Push All Images

When your code changes are ready for production:

```powershell
# Build all images and push to DockerHub with 'latest' tag
.\build-and-push.ps1 -DockerHubUsername yourusername
```

**With version tagging** (recommended for releases):
```powershell
# This pushes BOTH v1.2.0 AND latest tags
.\build-and-push.ps1 -DockerHubUsername yourusername -Tag v1.2.0
```

**Build specific services only**:
```powershell
.\build-and-push.ps1 -DockerHubUsername yourusername -Services dashboard,control-plane
```

**Build without pushing** (test builds):
```powershell
.\build-and-push.ps1 -DockerHubUsername yourusername -SkipPush
```

### Step 2: Deploy to Production Server

Copy `compose.prod.yaml` to your production server, then:

```bash
# Pull latest images
docker compose -f compose.prod.yaml pull

# Start/restart services
docker compose -f compose.prod.yaml up -d

# Check status
docker compose -f compose.prod.yaml ps

# View logs
docker compose -f compose.prod.yaml logs -f
```

### Step 3: Verify Deployment

- Dashboard: `http://your-server:8501`
- Control Plane API: `http://your-server:8002`
- Ingest Service API: `http://your-server:8003`

---

## Quick Reference

| Task | Command |
|------|---------|
| Build & push all | `.\build-and-push.ps1 -DockerHubUsername user` |
| Build & push with version | `.\build-and-push.ps1 -DockerHubUsername user -Tag v1.0.0` |
| Build only (no push) | `.\build-and-push.ps1 -DockerHubUsername user -SkipPush` |
| Build specific service | `.\build-and-push.ps1 -DockerHubUsername user -Services dashboard` |
| Pull images (prod server) | `docker compose -f compose.prod.yaml pull` |
| Start production | `docker compose -f compose.prod.yaml up -d` |
| Stop production | `docker compose -f compose.prod.yaml down` |
| View production logs | `docker compose -f compose.prod.yaml logs -f` |

---

## File Reference

| File | Purpose |
|------|---------|
| `compose.yaml` | Development - local builds with mounted volumes |
| `compose.prod.yaml` | Production - pulls from DockerHub |
| `build-and-push.ps1` | Builds and pushes all images to DockerHub |

---

## Troubleshooting

### "unauthorized: access to the requested resource is not authorized"
Run `docker login` and enter your DockerHub credentials.

### Build fails for a specific service
Run with `-SkipPush` to isolate build issues:
```powershell
.\build-and-push.ps1 -DockerHubUsername user -Services failing-service -SkipPush
```

### Images not updating on production
Make sure you've pulled the latest:
```bash
docker compose -f compose.prod.yaml pull
docker compose -f compose.prod.yaml up -d --force-recreate
```
