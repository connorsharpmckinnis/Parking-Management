FROM ultralytics/ultralytics:latest

WORKDIR /app

# The official Ultralytics image already has dependencies like OpenCV, PyTorch, and CUDA.
# We just need to sync our specific additional requirements.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# No port exposed as it's a worker client
CMD ["python", "worker.py"]
