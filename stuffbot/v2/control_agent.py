from pydantic import BaseModel
from openai import OpenAI
import base64
import os
class MovementCommand(BaseModel):
    linear_velocity: float  # meters per second
    angular_velocity: float  # radians per second
    description: str  # Removed duration since we're doing continuous control

class ChatHistory:
    def __init__(self, max_messages=3):
        self.max_messages = max_messages
        self.messages = []
        self.chat_dir = "chat_history"
        # Create chat history directory if it doesn't exist
        os.makedirs(self.chat_dir, exist_ok=True)
        self.request_counter = 0

    def save_exchange(self, exchange):
        """Save a single exchange to a file"""
        self.request_counter += 1
        filename = f"{self.chat_dir}/exchange_{self.request_counter}.txt"
        
        with open(filename, "w") as f:
            f.write("=== System Prompt ===\n")
            f.write(str(exchange["system"]) + "\n\n")
            f.write("=== User Content ===\n")
            f.write(str(exchange["user"]) + "\n\n")
            f.write("=== Assistant Response ===\n")
            f.write(str(exchange["assistant"]) + "\n")

    def add_exchange(self, system_prompt, user_content, assistant_response):
        # Add the new exchange
        exchange = {
            "system": system_prompt,
            "user": user_content,
            "assistant": assistant_response
        }
        self.messages.append(exchange)
        
        # Save the exchange to a file
        self.save_exchange(exchange)
        
        # Keep only the last max_messages
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)

    def get_messages_for_prompt(self, system_prompt, new_user_content):
        # Start with the system message
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add previous exchanges
        for exchange in self.messages:
            messages.append({"role": "user", "content": exchange["user"]})
            messages.append({"role": "assistant", "content": str(exchange["assistant"])})
        
        # Add the new user content
        messages.append({"role": "user", "content": new_user_content})
        
        return messages

# Create a global chat history instance
chat_history = ChatHistory()

class RobotState(BaseModel):
    current_linear_velocity: float
    current_angular_velocity: float

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def encode_image_bytes(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

def get_movement_command(image_data, robot_state: RobotState, is_path=False, history_length=1) -> MovementCommand:
    client = OpenAI()
    
    # Handle both file paths and image bytes
    if is_path:
        base64_image = encode_image(image_data)
    else:
        base64_image = encode_image_bytes(image_data)

    system_prompt = """You are a robot movement analyzer controlling a compact robot. Analyze images and provide safe navigation commands.

    CAMERA SETUP:
    - Mounted 5 feet (1.52m) above ground
    - Angled 45 degrees downward
    - Provides overhead perspective for navigation

    MISSION:
    - Primary goal is to inspect table surfaces and identify objects on them
    - When table surface is clearly visible, stop briefly to catalog visible objects
    - After inspection, resume search for other tables
    - Include observed table objects in movement command descriptions

    SAFETY & MOVEMENT:
    - Linear velocity: -1.0 to 1.0 m/s
      * CRITICAL: MUST STOP (0.0) if ANY object is within 2.0 meters
      * Stop (0.0) during turns and scanning
      * Slow approach (0.2-0.4 m/s) near tables
      * Max change: 0.2 m/s per update
    
    - Angular velocity: -1.5 to 1.5 rad/s
      * Scanning: 0.2-0.5 rad/s
      * Max change: 0.3 rad/s per update
      * For sharp turns (hairpin), set linear_velocity to 0.0 and only use angular_velocity

    - Safety Rules:
      * MANDATORY: Set linear_velocity to 0.0 and prefix description with "STOP:" when ANY object is within 2.0 meters
      * Never move forward if objects detected within 2.0 meters
      * Only move forward when table surface confirmed and at safe distance (>2.0m)
      * Maintain safe distance (>2.0m) from all objects
      * Conservative stopping is better than collision risk
      * When stopped, can perform hairpin turns by keeping linear_velocity at 0.0

    - Search Pattern:
      * Scan methodically when no table visible
      * Approach tables slowly and directly
      * Position for clear view of surface
      * Stop when table surface and objects are clearly visible for inspection
      * After inspection, continue searching for other tables"""

    user_content = [
        {
            "type": "text",
            "text": f"""Current robot state:
            - Linear velocity: {robot_state.current_linear_velocity:.2f} m/s
            - Angular velocity: {robot_state.current_angular_velocity:.2f} rad/s

            Analyze this image and provide updated movement commands for the robot to navigate safely.
            Look for table surfaces and any items on them. If a table is found, approach it carefully for optimal viewing.
            Ensure smooth velocity transitions from current state."""
        },
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
        }
    ]

    # Get messages including chat history if enabled
    if history_length > 0:
        # Update chat history max_messages to match history_length
        chat_history.max_messages = history_length
        messages = chat_history.get_messages_for_prompt(system_prompt, user_content)
    else:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=messages,
        response_format=MovementCommand,
        max_tokens=1000,
    )

    # Get the parsed response
    movement_command = completion.choices[0].message.parsed
    
    chat_history.add_exchange(system_prompt, user_content, movement_command)
    
    return movement_command