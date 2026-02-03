import json
import os
import time
import random
import uuid
import argparse
import signal
import logging
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("edge-simulator")

# Global flag for graceful shutdown
running = True

def signal_handler(signum, frame):
    global running
    logger.info("Signal received, stopping...")
    running = False

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

def generate_mock_heartbeat(status="online"):
    return {
        "status": status,
        "message": "Edge simulator operational"
    }

def main():
    parser = argparse.ArgumentParser(description="Simulate an edge parking vision device.")
    parser.add_argument("--broker", default=os.getenv("MQTT_BROKER", "localhost"), help="MQTT broker address")
    parser.add_argument("--port", type=int, default=int(os.getenv("MQTT_PORT", "1883")), help="MQTT broker port")
    parser.add_argument("--camera_id", default=os.getenv("CAMERA_ID", "1fa34d53-8153-4ae2-94fc-5f1200a6e49f"), help="UUID of the camera to simulate")
    parser.add_argument("--interval", type=int, default=int(os.getenv("UPDATE_INTERVAL", "15")), help="Seconds between updates")
    args = parser.parse_args()

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    
    logger.info(f"Connecting to MQTT broker at {args.broker}:{args.port}...")
    try:
        client.connect(args.broker, args.port, 60)
    except Exception as e:
        logger.error(f"Failed to connect: {e}")
        return

    client.loop_start()
    
    logger.info(f"Simulating camera: {args.camera_id}")
    logger.info(f"Update interval: {args.interval}s")

    try:
        while running:
            # 1. Send Heartbeat
            hb_topic = f"parking/camera/{args.camera_id}/heartbeat"
            hb_payload = generate_mock_heartbeat()
            client.publish(hb_topic, json.dumps(hb_payload))
            logger.info("Published Heartbeat")

            # 2. Send Event
            ev_topic = f"parking/camera/{args.camera_id}/event"
            ev_payload = generate_mock_event(args.camera_id)
            client.publish(ev_topic, json.dumps(ev_payload))
            logger.info(f"Published Event: {ev_payload['occupied_count']}/{ev_payload['total_slots']} occupied")

            # Sleep in small increments to check the 'running' flag frequently
            for _ in range(args.interval):
                if not running:
                    break
                time.sleep(1)
                
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        logger.info("Cleaning up...")
        client.loop_stop()
        client.disconnect()
        logger.info("Stopped.")

if __name__ == "__main__":
    main()

