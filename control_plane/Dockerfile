FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for psycopg2 and OpenCV
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY control_plane/requirements.txt ./control_plane/
RUN pip install --no-cache-dir -r control_plane/requirements.txt

COPY control_plane/ ./control_plane/
COPY database/ ./database/

WORKDIR /app/control_plane

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
