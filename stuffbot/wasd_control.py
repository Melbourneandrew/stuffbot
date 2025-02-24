#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import paho.mqtt.client as mqtt
from sshkeyboard import listen_keyboard, stop_listening
from datetime import datetime
import cv2
from process_image import ImageProcessor
from supabase_upload import supabase, upload_stuff_images
import time

# Constants
MQTT_BROKER_ADDRESS = "localhost"
MQTT_TOPIC = "robot/drive"
LINEAR_SPEED = 0.5  # m/s
ANGULAR_SPEED = 1.0  # rad/s
CONTROL_RATE = 30  # Hz - how often to process frames
MIN_TIME_BETWEEN_FRAMES = 1.0 / CONTROL_RATE

# MQTT Setup
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(MQTT_BROKER_ADDRESS)
client.loop_start()

# Camera and image processing setup
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

# Create images directory
images_dir = 'images'
os.makedirs(images_dir, exist_ok=True)

# Initialize image processor
image_processor = ImageProcessor.get_instance(
    display_enabled=True,
    save_images=False,
    conf_threshold=0.5
)

# Global variables for frame processing
last_process_time = 0
running = True

def process_camera_frame():
    global last_process_time
    current_time = time.time()
    
    # Rate limiting
    if current_time - last_process_time < MIN_TIME_BETWEEN_FRAMES:
        return
    
    cap.grab()  # Clear buffer
    ret, frame = cap.read()
    if not ret:
        print("Error reading from webcam")
        return
    
    try:
        # Process frame with image processor
        full_images, cropped_images, detections = image_processor.process_image(frame)
        print(detections)
        
        # Save and upload images if available
        if full_images and cropped_images:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            full_path = os.path.join(images_dir, f"full_{timestamp}.png")
            crop_path = os.path.join(images_dir, f"crop_{timestamp}.png")
            
            cv2.imwrite(full_path, full_images[0])
            cv2.imwrite(crop_path, cropped_images[0])
            
            # Uncomment to enable Supabase upload
            # success, error = upload_stuff_images(supabase, full_path, crop_path)
            # if not success:
            #     print(f"Failed to upload images: {error}")
        
        last_process_time = current_time
            
    except Exception as e:
        print(f"Error processing camera frame: {e}")

def press(key):
    global running
    if key.lower() == 'w':  # Forward
        client.publish(MQTT_TOPIC, "forward")
    elif key.lower() == 's':  # Backward
        client.publish(MQTT_TOPIC, "back")
    elif key.lower() == 'a':  # Left turn
        client.publish(MQTT_TOPIC, "left")
    elif key.lower() == 'd':  # Right turn
        client.publish(MQTT_TOPIC, "right")
    elif key.lower() == 'q':  # Quit
        running = False
        stop_listening()

def release(key):
    # Stop motors when key is released
    client.publish(MQTT_TOPIC, "stop")

def cleanup():
    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()
    client.publish(MQTT_TOPIC, "stop")
    client.loop_stop()
    client.disconnect()

try:
    print("WASD to control, Q to quit")
    # Start keyboard listener in a non-blocking way
    listen_keyboard(
        on_press=press,
        on_release=release,
    )
    
    # Main processing loop
    while running:
        process_camera_frame()
        time.sleep(0.01)  # Small sleep to prevent CPU spinning

except Exception as e:
    print(f"Error: {e}")
finally:
    cleanup()
    print("Shutdown complete.")

if __name__ == '__main__':
    pass  # Script runs directly from the try-except block above 