import bz2
import json
import os
import time
import random
import uuid
import argparse
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

def generate_mock_event(camera_id, total_slots=10):
    occupied = random.randint(0, total_slots)
    
    # Simulate per-spot data
    spot_details = []
    for i in range(total_slots):
        spot_details.append({
            "spot_id": f"spot_{i+1}",
            "occupied": i < occupied
        })
        
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "occupied_count": occupied,
        "free_count": total_slots - occupied,
        "total_slots": total_slots,
        "metadata_json": {
            "spot_details": spot_details,
            "source": "edge_simulator"
        }
    }

def generate_mock_heartbeat(status="healthy"):
    return {
        "status": status,
        "message": "Edge simulator operational"
    }

def main():
    parser = argparse.ArgumentParser(description="Simulate an edge parking vision device.")
    parser.add_argument("--broker", default=os.getenv("MQTT_BROKER", "localhost"), help="MQTT broker address")
    parser.add_argument("--port", type=int, default=int(os.getenv("MQTT_PORT", "1883")), help="MQTT broker port")
    parser.add_argument("--camera_id", default=os.getenv("CAMERA_ID", str(uuid.uuid4())), help="UUID of the camera to simulate")
    parser.add_argument("--interval", type=int, default=int(os.getenv("UPDATE_INTERVAL", "10")), help="Seconds between updates")
    args = parser.parse_args()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    
    print(f"Connecting to MQTT broker at {args.broker}:{args.port}...")
    try:
        client.connect(args.broker, args.port, 60)
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    client.loop_start()
    
    print(f"Simulating camera: {args.camera_id}")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            # 1. Send Heartbeat
            hb_topic = f"parking/camera/{args.camera_id}/heartbeat"
            hb_payload = generate_mock_heartbeat()
            client.publish(hb_topic, json.dumps(hb_payload))
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Published Heartbeat")

            # 2. Send Event
            ev_topic = f"parking/camera/{args.camera_id}/event"
            ev_payload = generate_mock_event(args.camera_id)
            client.publish(ev_topic, json.dumps(ev_payload))
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Published Event: {ev_payload['occupied_count']}/{ev_payload['total_slots']} occupied")

            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopping simulator...")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
