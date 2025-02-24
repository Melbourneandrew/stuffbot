# StuffBot_manual.py
# Uses WASD to move the robotzzz
# Uses space bar to invoke Yolo to catalog items

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import paho.mqtt.client as mqtt
from sshkeyboard import listen_keyboard, stop_listening
from StuffBot_Yolo import StuffBot_Detect
from distance_detector import DistanceDetector  # Add this import
from StuffBot_Yolo import StuffBot_Continuous_Detect
import signal

# ------------------------------------------------------------------------------------
# Constants & Setup
# ------------------------------------------------------------------------------------
MQTT_BROKER_ADDRESS = "localhost"
MQTT_TOPIC = "robot/drive"

os.environ["DISPLAY"] = ":0"

# Create MQTT client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(MQTT_BROKER_ADDRESS)
client.loop_start()

# Initialize distance detector
distance_detector = DistanceDetector()

# StuffBot_Continuous_Detect()

def press(key):
    if key.lower() == 'w':  # Forward
        client.publish(MQTT_TOPIC, "forward")
        closest = findObjects(conf_threshold=0.5, save_images=False)  # Don't save during movement
        if closest:
            print(f"\nClosest object: {closest['class_name']} at {closest['distance']:.2f}m")
    elif key.lower() == 's':  # Backward
        client.publish(MQTT_TOPIC, "back") 
    elif key.lower() == 'a':  # Left turn
        client.publish(MQTT_TOPIC, "left")
    elif key.lower() == 'd':  # Right turn
        client.publish(MQTT_TOPIC, "right")
    elif key.lower() == 'q':  # Quit
        stop_listening()
    elif key == 'space':  # Modified space bar detection
        # Explicitly set save_images=True for space bar presses
        findObjects(conf_threshold=0.1, save_images=True)
        


def findObjects(conf_threshold=0.1, save_images=False):
    # Pass the save_images parameter through to StuffBot_Detect
    detections = StuffBot_Detect(conf_threshold=conf_threshold, save_images=save_images)
    closest_object = None
    min_distance = float('inf')
    
    if detections:
        print("\nDetected Objects:")
        for det in detections:
            try:
                bbox = [float(x) for x in det['box']]
                confidence = float(det['confidence'])
                class_name = det['class_name']
                
                distance = distance_detector.calculate_object_distance(bbox)
                print(f"- {class_name} (Confidence: {confidence:.2f}, Distance: {distance}m)")
                
                # Track closest object
                if distance < min_distance:
                    min_distance = distance
                    closest_object = {
                        'class_name': class_name,
                        'distance': distance,
                        'confidence': confidence
                    }
                    
            except Exception as e:
                print(f"Error processing detection: {e}")
                print(f"Detection data: {det}")
    
    return closest_object


def release(key):
    # Stop motors when key is released
    client.publish(MQTT_TOPIC, "stop")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print('\nGracefully shutting down...')
    stop_listening()  # Stop keyboard listener
    client.publish(MQTT_TOPIC, "stop")
    client.loop_stop()
    client.disconnect()
    print("Shutdown complete.")
    sys.exit(0)

try:
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    print("WASD to control, Q to quit")
    listen_keyboard(
        on_press=press,
        on_release=release,
    )

except Exception as e:
    print(f"Error: {e}")
finally:
    # Clean up
    client.publish(MQTT_TOPIC, "stop")
    client.loop_stop()
    client.disconnect()
    print("Shutdown complete.")