import cv2
import paho.mqtt.client as mqtt
import json
import signal
import sys
import os
from dotenv import load_dotenv
from control_agent import ControlAgent, RobotState
import time
from datetime import datetime
import argparse
from process_image import ImageProcessor
from supabase_upload import supabase, upload_stuff_images

load_dotenv()

# MQTT setup
MQTT_BROKER_ADDRESS = "localhost"
MQTT_TOPIC = "robot/drive"

# Control parameters
CONTROL_RATE = 2  # Hz - how often to get new commands
MIN_TIME_BETWEEN_COMMANDS = 1.0 / CONTROL_RATE
TIMEOUT_DURATION = 5.0  # seconds before stopping if no new commands received

class RobotController:
    def __init__(self):
        self.last_command_time = time.time()
        self.running = True
        self.current_linear_velocity = 0.0
        self.current_angular_velocity = 0.0
        
        # Create images directory
        self.images_dir = 'images'
        os.makedirs(self.images_dir, exist_ok=True)
        
        # MQTT setup
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.connect(MQTT_BROKER_ADDRESS)
        self.client.loop_start()
        
        # Camera setup
        self.cap = cv2.VideoCapture(0)
        self.setup_camera()
        
        # Register signal handler
        signal.signal(signal.SIGINT, self.signal_handler)
        
        self.control_agent = ControlAgent()
        
        # Initialize image processor
        self.image_processor = ImageProcessor.get_instance(
            display_enabled=True,
            save_images=False,
            conf_threshold=0.5
        )

    def setup_camera(self):
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

    def send_movement_command(self, linear_vel, angular_vel):
        data = {
            "linear_velocity": linear_vel,
            "angular_velocity": angular_vel * 1.15
        }
        self.flush_mqtt_topic()
        self.client.publish(MQTT_TOPIC, json.dumps(data), retain=False)
        self.last_command_time = time.time()
        # Update current velocities
        self.current_linear_velocity = linear_vel
        self.current_angular_velocity = angular_vel

    def stop_robot(self):
        self.send_movement_command(0.0, 0.0)
        print("Robot stopped")

    def flush_mqtt_topic(self):
        """Clear any retained messages on the control topic."""
        self.client.publish(MQTT_TOPIC, "", retain=True)
        print(f"Flushed MQTT topic: {MQTT_TOPIC}")

    def cleanup(self):
        self.stop_robot()
        self.flush_mqtt_topic()
        if self.cap is not None:
            self.cap.release()
        self.client.loop_stop()
        self.client.disconnect()
        cv2.destroyAllWindows()

    def signal_handler(self, sig, frame):
        print('\nGracefully shutting down...')
        self.running = False

    def run(self):
        print("StuffBot Real-time Control")
        print("Press Ctrl+C to quit")

        last_process_time = 0

        try:
            while self.running:
                current_time = time.time()
                
                # Check for timeout
                if current_time - self.last_command_time > TIMEOUT_DURATION:
                    print("Command timeout - stopping robot")
                    self.stop_robot()
                
                # Rate limiting
                if current_time - last_process_time < MIN_TIME_BETWEEN_COMMANDS:
                    time.sleep(0.01)  # Small sleep to prevent CPU spinning
                    continue
                
                # Capture frame
                self.cap.grab()  # Clear buffer
                ret, frame = self.cap.read()
                if not ret:
                    print("Error reading from webcam")
                    break
                
                try:
                    # Process frame with image processor
                    full_images, cropped_images, detections = self.image_processor.process_image(frame)
                    
                    # Save and upload images if available
                    if full_images and cropped_images:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        full_path = os.path.join(self.images_dir, f"full_{timestamp}.png")
                        crop_path = os.path.join(self.images_dir, f"crop_{timestamp}.png")
                        
                        cv2.imwrite(full_path, full_images[0])
                        cv2.imwrite(crop_path, cropped_images[0])
                        
                        success, error = upload_stuff_images(supabase, full_path, crop_path)
                        if not success:
                            print(f"Failed to upload images: {error}")
                    
                    # Print detections
                    # if detections:
                    #     print("\nDetected Objects:")
                    #     for det in detections:
                    #         print(f"- {det['class_name']} (ID: {det['object_id']}) at confidence {det['confidence']:.2f}")
                    
                    # Use the first full image for display and control if available, otherwise use original frame
                    display_frame = full_images[0] if full_images else frame
                    
                    # Convert frame to JPEG format for the control agent
                    _, buffer = cv2.imencode('.jpg', display_frame)
                    image_bytes = buffer.tobytes()
                    
                    # # Create robot state
                    # robot_state = RobotState(
                    #     current_linear_velocity=self.current_linear_velocity,
                    #     current_angular_velocity=self.current_angular_velocity
                    # )
                    
                    # # Get movement commands from LLM
                    # movement = self.control_agent.get_movement_command(image_bytes, robot_state, is_path=False)
                    
                    # # Display the proposed movement
                    # print("\nExecuting Movement Command:")
                    # print(f"Mode: {self.control_agent.current_mode.name}")
                    # print(f"(lin, ang): ({movement.linear_velocity:.2f}, {movement.angular_velocity:.2f}) m/s")
                    # print(f"Description: {movement.description}")
                    
                    # self.send_movement_command(
                    #     movement.linear_velocity,
                    #     movement.angular_velocity
                    # )

                    # time.sleep(1)

                    # print("STOPPED BY SCRIPT")
                    # self.stop_robot()
                    
                    last_process_time = time.time()
                    
                except Exception as e:
                    print(f"Error getting movement command: {e}")
                    self.stop_robot()

        except KeyboardInterrupt:
            print("\nProgram interrupted by user")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.cleanup()
            print("Shutdown complete.")

def main():
    controller = RobotController()
    controller.run()

if __name__ == "__main__":
    main()
