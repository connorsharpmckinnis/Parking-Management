import time
import os
import requests
import subprocess
import json

# Configuration
CONTROL_PLANE_URL = os.getenv("CONTROL_PLANE_URL", "http://control-plane:8000")
RECONCILE_INTERVAL = int(os.getenv("RECONCILE_INTERVAL", "10"))
WORKER_IMAGE = os.getenv("WORKER_IMAGE", "parking-vision-worker:latest")

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
            print(f"Starting worker for {camera['name']}...")
            start_worker(camera)
        elif not should_run and is_running:
            print(f"Stopping worker for {camera['name']}...")
            stop_worker(container_name)
    
    # Cleanup rogue containers
    desired_names = {f"parking-worker-{c['id']}" for c in desired}
    for name in actual_names:
        if name not in desired_names:
            print(f"Removing rogue container: {name}")
            stop_worker(name)

def start_worker(camera):
    # Construct docker run command
    # Windows Docker Desktop usually exposes docker.sock
    cmd = [
        "docker", "run", "-d",
        "--name", f"parking-worker-{camera['id']}",
        "--restart", "unless-stopped",
        "--network", "parking-management_parking-net", # Connect to the compose network
        "-e", f"CAMERA_ID={camera['id']}",
        "-e", f"STREAM_URL={camera['stream_url']}",
        "-e", f"API_ENDPOINT={CONTROL_PLANE_URL}",
        "-e", f"POLL_INTERVAL={camera['processing_interval_sec']}",
        "-e", f"ZONE_CONFIG={json.dumps(camera['geometry'])}",
        "-e", f"DETECTION_CLASSES={json.dumps(camera.get('detection_classes', [2, 3, 5, 7]))}",
        WORKER_IMAGE
    ]
    subprocess.run(cmd)

def stop_worker(name):
    subprocess.run(["docker", "stop", name])
    subprocess.run(["docker", "rm", name])

if __name__ == "__main__":
    while True:
        reconcile()
        time.sleep(RECONCILE_INTERVAL)
