import cv2
import paho.mqtt.client as mqtt
import json
import signal
import sys
import os
from dotenv import load_dotenv
from control_agent import get_movement_command
import time
from datetime import datetime

load_dotenv()

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
    cleanup(None)  # Pass None since we can't access cap from here
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
    print(f"Executing movement for {duration} seconds...")
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
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    # Disable audio capture
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

    # Create images directory if it doesn't exist
    os.makedirs('images', exist_ok=True)

    print("StuffBot Human-in-Loop Control")
    print("Press Ctrl+C to quit, or press ENTER to execute each command")

    try:
        while True:
            # Capture frame. GRAB ONE OFF THE BUFFER TO GET THE LATEST FRAME
            cap.grab()
            ret, frame = cap.read()
            if not ret:
                print("Error reading from webcam")
                break
             
            # Generate timestamp for unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            image_path = f"images/frame_{timestamp}.jpg"
            
            # Save frame to file
            # cv2.imwrite(image_path, frame)
            
            # Get movement commands from LLM using the saved image
            try:
                movement = get_movement_command(image_path, is_path=True)
                
                # Display the proposed movement
                print("\nProposed Movement Command:")
                print(f"Vel (lin, ang): ({movement.linear_velocity:.2f}, {movement.angular_velocity:.2f}) m/s")
                print(f"Duration: {movement.duration:.1f} s")
                print(f"Description: {movement.description}")
                print("\nPress ENTER to execute, or Ctrl+C to quit...")
                
                # Wait for user input and close the image window
                user_input = input()
                cv2.destroyAllWindows()
                
                if user_input == '':  # Wait for ENTER
                    # Execute the movement command
                    send_movement_command(
                        movement.linear_velocity,
                        movement.angular_velocity * 1.3,
                        movement.duration + 1.5
                    )
                
            except Exception as e:
                print(f"Error getting movement command: {e}")

    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        cleanup(cap)
        print("Shutdown complete.")

if __name__ == "__main__":
    main()
