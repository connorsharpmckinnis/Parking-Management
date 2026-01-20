FROM python:3.11-slim

WORKDIR /app

# Install Podman to allow reconcile loop to manage containers
# Note: This might require specific volume mounts of the socket/pipe
RUN apt-get update && apt-get install -y \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "reconciler.py"]
