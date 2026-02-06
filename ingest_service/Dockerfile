FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/*

# Copy files from the updated build context (Project Root)
COPY ingest_service/requirements.txt ./ingest_service/
RUN pip install --no-cache-dir -r ingest_service/requirements.txt

# Copy service code and shared database
COPY ingest_service/ ./ingest_service/
COPY database/ ./database/

WORKDIR /app/ingest_service

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
