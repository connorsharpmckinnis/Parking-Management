import time
import os
import requests
import subprocess
import json

# Configuration
CONTROL_PLANE_URL = os.getenv("CONTROL_PLANE_URL", "http://control-plane:8000")
INGEST_SERVICE_URL = os.getenv("INGEST_SERVICE_URL", "http://ingest-service:8001")
RECONCILE_INTERVAL = int(os.getenv("RECONCILE_INTERVAL", "10"))
WORKER_IMAGE = os.getenv("WORKER_IMAGE", "parking-vision-worker:latest")
FORCE_CPU = os.getenv("FORCE_CPU", "false").lower() == "true"
MOUNT_WORKER_CODE = os.getenv("MOUNT_WORKER_CODE") # Optional: host path to vision_worker for dev
DOCKER_NETWORK = os.getenv("DOCKER_NETWORK", "parking-management_parking-net")

def get_desired_state():
    try:
        response = requests.get(f"{CONTROL_PLANE_URL}/cameras", timeout=10)
        return response.json()
    except Exception as e:
        print(f"Failed to fetch desired state: {e}")
        return []

def get_actual_state():
    # Calling Docker CLI to get running containers
    # We look for containers with prefix 'parking-worker-'
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{json .}}", "--filter", "name=parking-worker-"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            # Docker returns one JSON object per line
            containers = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    containers.append(json.loads(line))
            return containers
        return []
    except Exception as e:
        print(f"Failed to fetch actual state: {e}")
        return []

def reconcile():
    print(f"[{time.ctime()}] Starting reconciliation...")
    
    desired = get_desired_state()
    actual = get_actual_state()
    
    actual_names = set()
    for c in actual:
        # Docker format {{json .}} returns key 'Names' as a string "name"
        name = c.get('Names', '')
        actual_names.add(name)
    
    for camera in desired:
        container_name = f"parking-worker-{camera['id']}"
        should_run = camera['desired_state'] == "running"
        is_running = container_name in actual_names
        
        if should_run and not is_running:
            print(f"[{time.ctime()}] Starting worker for {camera['name']} ({camera['id']})...")
            start_worker(camera)
        elif not should_run and is_running:
            print(f"[{time.ctime()}] Stopping worker for {camera['name']} ({camera['id']})...")
            stop_worker(container_name)
        elif should_run and is_running:
            # Optionally check if container is actually running or restarting
            pass

    
    # Cleanup rogue containers
    desired_names = {f"parking-worker-{c['id']}" for c in desired}
    for name in actual_names:
        if name not in desired_names:
            print(f"Removing rogue container: {name}")
            stop_worker(name)

def gpu_available():
    if FORCE_CPU:
        return False
    try:
        result = subprocess.run(
            ["nvidia-smi"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.SubprocessError):
        return False

def start_worker(camera):
    # Force remove any existing container with this name (crashed, legacy, etc)
    # to ensure we always start fresh with the latest image.
    container_name = f"parking-worker-{camera['id']}"
    subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

    cmd = [
        "docker", "run", "-d",
        "--name", container_name,
        "--restart", "unless-stopped",
        "--network", DOCKER_NETWORK,
        "--ipc", "host",
    ]

    if gpu_available():
        cmd.extend(["--runtime", "nvidia"])
        cmd.extend(["--gpus", "all"])
        cmd.extend(["-e", "NVIDIA_VISIBLE_DEVICES=all"])
        print(f"[{time.ctime()}] GPU detected — starting worker with GPU support")
    else:
        cmd.extend(["-e", "CUDA_VISIBLE_DEVICES="])
        print(f"[{time.ctime()}] GPU disabled/not found — starting worker in CPU mode")

    if MOUNT_WORKER_CODE:
        # Note: MOUNT_WORKER_CODE should be an absolute path from the HOST perspective
        cmd.extend(["-v", f"{MOUNT_WORKER_CODE}:/app"])
        print(f"[{time.ctime()}] Mounting worker code from: {MOUNT_WORKER_CODE}")

    cmd.extend([
        "-e", f"CAMERA_ID={camera['id']}",
        "-e", f"STREAM_URL={camera['stream_url']}",
        "-e", f"API_ENDPOINT={INGEST_SERVICE_URL}",
        "-e", f"CONFIG_ENDPOINT={CONTROL_PLANE_URL}",
        "-e", f"POLL_INTERVAL={camera['processing_interval_sec']}",
        "-e", f"ZONE_CONFIG={json.dumps(camera['geometry'])}",
        "-e", f"DETECTION_CLASSES={json.dumps(camera.get('detection_classes', [2, 3, 5, 7]))}",
        "-e", f"DETECTION_CONFIDENCE={camera.get('detection_confidence', 0.25)}",
        "-e", f"SAHI_ENABLED={str(camera.get('sahi_enabled', False)).lower()}",
        "-e", f"SAHI_TILE_SIZE={camera.get('sahi_tile_size', 640)}",
        "-e", f"SAHI_OVERLAP_RATIO={camera.get('sahi_overlap_ratio', 0.25)}",
        "-e", f"OCCUPANCY_BOTTOM_PCT={camera.get('occupancy_bottom_pct', 0.33)}",
        "-e", f"OCCUPANCY_MIN_OVERLAP={camera.get('occupancy_min_overlap', 0.30)}",
        "-e", f"MODEL_PATH={camera.get('model_version', 'rtdetr-l.pt')}",
        WORKER_IMAGE
    ])

    subprocess.run(cmd)

def stop_worker(name):
    subprocess.run(["docker", "stop", name])
    subprocess.run(["docker", "rm", name])

if __name__ == "__main__":
    while True:
        reconcile()
        time.sleep(RECONCILE_INTERVAL)
