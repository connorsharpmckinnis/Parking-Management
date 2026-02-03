import os
import json
import time
import requests
import paho.mqtt.client as mqtt
from datetime import datetime

# Configuration
MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt-broker")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
INGEST_SERVICE_URL = os.getenv("INGEST_SERVICE_URL", "http://ingest-service:8001")

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"Connected to MQTT Broker: {MQTT_BROKER}")
        # Subscribe to all camera topics
        # parking/camera/{id}/event
        # parking/camera/{id}/heartbeat
        client.subscribe("parking/camera/+/+")
        print("Subscribed to parking/camera/+/+")
    else:
        print(f"Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    try:
        topic_parts = msg.topic.split('/')
        if len(topic_parts) != 4:
            return

        camera_id = topic_parts[2]
        msg_type = topic_parts[3] # 'event' or 'heartbeat'
        
        payload = json.loads(msg.payload.decode())
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Received {msg_type} for {camera_id}")
        
        # Forward to Ingest Service
        endpoint = f"{INGEST_SERVICE_URL}/cameras/{camera_id}/{msg_type}"
        response = requests.post(endpoint, json=payload, timeout=5)
        
        if response.status_code == 200:
            print(f"  → Successfully forwarded to Ingest Service")
        else:
            print(f"  → Failed to forward: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"Error processing message: {e}")

def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"Starting bridge. Connecting to {MQTT_BROKER}...")
    
    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            break
        except Exception as e:
            print(f"Connection failed ({e}), retrying in 5s...")
            time.sleep(5)

    client.loop_forever()

if __name__ == "__main__":
    main()
