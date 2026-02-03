FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

ENV MQTT_BROKER=mqtt-broker
ENV MQTT_PORT=1883
ENV INGEST_SERVICE_URL=http://ingest-service:8001

CMD ["python", "-u", "main.py"]
