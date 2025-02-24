import cv2
import paho.mqtt.client as mqtt
import json
import signal
import sys
import os
from dotenv import load_dotenv
from control_agent import get_movement_command, RobotState
import time
from datetime import datetime
import argparse

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
        os.makedirs('images', exist_ok=True)
        
        # MQTT setup
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.connect(MQTT_BROKER_ADDRESS)
        self.client.loop_start()
        
        # Camera setup
        self.cap = cv2.VideoCapture(0)
        self.setup_camera()
        
        # Register signal handler
        signal.signal(signal.SIGINT, self.signal_handler)

    def setup_camera(self):
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))

    def send_movement_command(self, linear_vel, angular_vel):
        data = {
            "linear_velocity": linear_vel,
            "angular_velocity": angular_vel
        }
        self.client.publish(MQTT_TOPIC, json.dumps(data))
        self.last_command_time = time.time()
        # Update current velocities
        self.current_linear_velocity = linear_vel
        self.current_angular_velocity = angular_vel

    def stop_robot(self):
        self.send_movement_command(0.0, 0.0)
        print("Robot stopped")

    def cleanup(self):
        self.stop_robot()
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
                    # Generate timestamp and save frame
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                    image_path = f"images/frame_{timestamp}.jpg"
                    cv2.imwrite(image_path, frame)
                    
                    # Convert frame to JPEG format
                    _, buffer = cv2.imencode('.jpg', frame)
                    image_bytes = buffer.tobytes()
                    
                    # Create robot state
                    robot_state = RobotState(
                        current_linear_velocity=self.current_linear_velocity,
                        current_angular_velocity=self.current_angular_velocity
                    )
                    
                    # Get movement commands from LLM
                    movement = get_movement_command(image_bytes, robot_state, is_path=False)
                    
                    # Display the proposed movement
                    print("\nExecuting Movement Command:")
                    # print(f"Current Vel (lin, ang): ({self.current_linear_velocity:.2f}, {self.current_angular_velocity:.2f}) m/s")
                    print(f"(lin, ang): ({movement.linear_velocity:.2f}, {movement.angular_velocity:.2f}) m/s")
                    print(f"Description: {movement.description}")
                    
                    self.send_movement_command(
                        movement.linear_velocity * 0.5,
                        movement.angular_velocity
                    )

                    time.sleep(2)

                    print("STOPPED BY SCRIPT")
                    self.stop_robot()
                    
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
