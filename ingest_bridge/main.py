import os
import json
import time
import requests
import paho.mqtt.client as mqtt
import logging
import signal
from datetime import datetime

# Configuration
MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
INGEST_SERVICE_URL = os.getenv("INGEST_SERVICE_URL", "http://ingest-service:8001")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ingest-bridge")

# Global flag for graceful shutdown
running = True

def signal_handler(signum, frame):
    global running
    logger.info("Signal received, stopping...")
    running = False

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logger.info(f"Connected to MQTT Broker: {MQTT_BROKER}")
        client.subscribe("parking/camera/+/+")
        logger.info("Subscribed to parking/camera/+/+")
    else:
        logger.error(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    try:
        topic_parts = msg.topic.split('/')
        if len(topic_parts) != 4:
            return

        camera_id = topic_parts[2]
        msg_type = topic_parts[3] # 'event' or 'heartbeat'
        
        payload = json.loads(msg.payload.decode())
        
        logger.info(f"Received {msg_type} for {camera_id}")
        
        # Forward to Ingest Service
        endpoint = f"{INGEST_SERVICE_URL}/cameras/{camera_id}/{msg_type}"
        try:
            response = requests.post(endpoint, json=payload, timeout=5)
            if response.status_code == 200:
                logger.info(f"  → Successfully forwarded to Ingest Service")
            else:
                logger.warning(f"  → Failed to forward: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"  → Connection error to Ingest Service: {e}")

    except Exception as e:
        logger.error(f"Error processing message: {e}")

def main():
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    logger.info(f"Starting bridge. Connecting to {MQTT_BROKER}...")
    
    connected = False
    while running and not connected:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            connected = True
        except Exception as e:
            logger.error(f"Connection failed ({e}), retrying in 5s...")
            # Check 'running' flag during retry sleep
            for _ in range(5):
                if not running:
                    break
                time.sleep(1)

    if connected:
        client.loop_start()
        while running:
            time.sleep(1)
        
        logger.info("Cleaning up...")
        client.loop_stop()
        client.disconnect()
        logger.info("Stopped.")

if __name__ == "__main__":
    main()

