FROM ultralytics/ultralytics:latest

WORKDIR /app

# The official Ultralytics image already has dependencies like OpenCV, PyTorch, and CUDA.
# We just need to sync our specific additional requirements.
COPY vision_worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY vision_worker/ .

CMD ["python", "worker.py"]
