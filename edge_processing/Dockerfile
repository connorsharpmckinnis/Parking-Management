FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy simulator script
COPY simulate_edge.py .

# Environment variables for the simulator
ENV MQTT_BROKER=mqtt-broker
ENV MQTT_PORT=1883
ENV CAMERA_ID=""
ENV UPDATE_INTERVAL=10

# Run the simulator
# We use python -u for unbuffered output to see logs in docker logs
CMD ["sh", "-c", "python -u simulate_edge.py --broker $MQTT_BROKER --port $MQTT_PORT --camera_id ${CAMERA_ID:-$(cat /proc/sys/kernel/random/uuid)} --interval $UPDATE_INTERVAL"]
