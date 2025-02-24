import cv2
import paho.mqtt.client as mqtt
import json
import signal
import sys
import os
from datetime import datetime
import time

# MQTT setup
MQTT_BROKER_ADDRESS = "localhost"
MQTT_TOPIC = "robot/drive"

# Create MQTT client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(MQTT_BROKER_ADDRESS)
client.loop_start()

def cleanup(cap):
    """Cleanup resources and stop the robot"""
    stop_robot()
    if cap is not None:
        cap.release()
    client.loop_stop()
    client.disconnect()

def signal_handler(sig, frame):
    print('\nGracefully shutting down...')
    cleanup(None)
    sys.exit(0)

def stop_robot():
    """Send stop command to the robot"""
    stop_data = {
        "linear_velocity": 0.0,
        "angular_velocity": 0.0
    }
    client.publish(MQTT_TOPIC, json.dumps(stop_data))
    print("Robot stopped")

def send_movement_command(linear_vel, angular_vel, duration):
    """Send movement command and handle the duration"""
    data = {
        "linear_velocity": linear_vel,
        "angular_velocity": angular_vel
    }
    client.publish(MQTT_TOPIC, json.dumps(data))
    print(f"Turning for {duration} seconds...")
    time.sleep(duration)
    stop_robot()

def main():
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialize webcam
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 15)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    # Create images directory if it doesn't exist
    os.makedirs('images', exist_ok=True)

    try:
        # Take first picture
        cap.grab()
        ret, frame = cap.read()
        if not ret:
            print("Error reading from webcam")
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        image_path = f"images/frame_before_{timestamp}.jpg"
        cv2.imwrite(image_path, frame)
        print(f"Took first picture: {image_path}")
        
        # Turn for 3 seconds
        send_movement_command(0.0, 0.5, 3.0)  # 0.5 rad/s angular velocity
        
        # Take second picture
        cap.grab()
        ret, frame = cap.read()
        if not ret:
            print("Error reading from webcam")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        image_path = f"images/frame_after_{timestamp}.jpg"
        cv2.imwrite(image_path, frame)
        print(f"Took second picture: {image_path}")

    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cleanup(cap)
        print("Shutdown complete.")

if __name__ == "__main__":
    main() 