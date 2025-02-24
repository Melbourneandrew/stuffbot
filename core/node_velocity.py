#!/usr/bin/env python3

# Adds the lib directory to the Python path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import paho.mqtt.client as mqtt
import json
import time

# ------------------------------------------------------------------------------------
# Constants & Setup
# ------------------------------------------------------------------------------------
MQTT_BROKER_ADDRESS = "localhost"
MQTT_TOPIC = "robot/drive"

# Create MQTT client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(MQTT_BROKER_ADDRESS)
client.loop_start()

def normalize_angular_velocity(input_value):
    """
    Maps input from -1 to 1 to either -2 to -1 (negative) or 1 to 2 (positive)
    """
    if input_value > 0:
        # Map 0 to 1 → 1 to 2
        return 1.0 + input_value
    elif input_value < 0:
        # Map -1 to 0 → -2 to -1
        return -2.0 + abs(input_value)
    return 0.0  # When input is exactly 0

def get_velocity_input():
    try:
        duration = float(input("\nEnter duration in seconds (or 'q' to quit): "))
        linear = float(input("Enter linear velocity (-1.0 to 1.0): "))
        angular_input = float(input("Enter angular velocity (-1.0 to 1.0): "))
        
        # Clamp input values between -1.0 and 1.0
        linear = max(min(linear, 1.0), -1.0)
        angular_input = max(min(angular_input, 1.0), -1.0)
        
        # Convert angular input to actual angular velocity
        angular = normalize_angular_velocity(angular_input)
        
        return duration, linear, angular
    except ValueError:
        return None, None, None

try:
    print("Enter duration and velocity values (use 'q' to quit)")
    while True:
        duration, linear, angular = get_velocity_input()
        
        if duration is None:  # User entered 'q' or invalid input
            print("\nExiting program...")
            break
            
        data = {
            "linear_velocity": linear,
            "angular_velocity": angular
        }
        
        json_data = json.dumps(data)
        client.publish(MQTT_TOPIC, json_data)
        print(f"Published: {json_data}")
        print(f"Waiting for {duration} seconds...")
        time.sleep(duration)
        
        # Send stop command after duration
        stop_data = {
            "linear_velocity": 0.0,
            "angular_velocity": 0.0
        }
        client.publish(MQTT_TOPIC, json.dumps(stop_data))
        print("Stopped")
        print("\nReady for next command...")

except KeyboardInterrupt:
    print("\nProgram interrupted by user")
except Exception as e:
    print(f"Error: {e}")
finally:
    # Clean up
    stop_data = {
        "linear_velocity": 0.0,
        "angular_velocity": 0.0
    }
    client.publish(MQTT_TOPIC, json.dumps(stop_data))
    client.loop_stop()
    client.disconnect()
    print("Shutdown complete.") 