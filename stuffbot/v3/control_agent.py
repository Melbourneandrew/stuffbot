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
        self.max_messages = max_messages - 1  # Subtract 1 to account for new message
        self.messages = []
        self.chat_dir = "chat_history"
        # Create chat history directory if it doesn't exist
        os.makedirs(self.chat_dir, exist_ok=True)
        self.request_counter = 0

    def save_exchange(self, exchange):
        """Save a single exchange to a file"""
        self.request_counter += 1
        filename = f"{self.chat_dir}/exchange_{self.request_counter}.txt"
        
        def truncate_content(content):
            if isinstance(content, str):
                return content[:500]
            elif isinstance(content, list):
                truncated = []
                for item in content:
                    if item.get("type") == "text":
                        truncated_item = item.copy()
                        truncated_item["text"] = item["text"][:500]
                        truncated.append(truncated_item)
                    else:
                        truncated.append(item)
                return truncated
            return content

        with open(filename, "w") as f:
            f.write("=== System Prompt ===\n")
            f.write(str(exchange["system"]) + "\n\n")
            f.write("=== Chat History ===\n")
            # Write all messages from the history
            for msg in exchange["history"]:
                role = msg["role"]
                content = truncate_content(msg["content"])
                f.write(f"[{role}]: {content}\n")
            f.write("\n=== Current Exchange ===\n")
            f.write(f"User: {str(truncate_content(exchange['user']))}\n")
            f.write(f"Assistant: {str(exchange['assistant'])}\n")

    def add_exchange(self, system_prompt, user_content, assistant_response):
        # Get current chat history before adding new exchange
        history_messages = []
        for msg in self.messages:
            history_messages.extend([
                {"role": "user", "content": msg["user"]},
                {"role": "assistant", "content": str(msg["assistant"])}
            ])

        # Add the new exchange
        exchange = {
            "system": system_prompt,
            "history": history_messages,
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

    system_prompt = """You are a robot movement analyzer controlling a compact robot. Your mission is to catalog items on tables in the environment.

    PRIMARY OBJECTIVES:
    1. Execute hairpin search pattern to find tables
    2. When a table is found, position for optimal viewing
    3. Stop and catalog all visible objects on table surfaces
    4. After cataloging, resume hairpin search pattern
    
    CAMERA SPECIFICATIONS:
    - Mounted 5 feet (1.52m) above ground
    - Angled 45 degrees downward
    - Provides overhead perspective for navigation

    MOVEMENT PARAMETERS:
    - Linear velocity: -1.0 to 1.0 m/s
      * Maximum acceleration/deceleration: 0.2 m/s per update
      * Use 0.2-0.4 m/s for careful approach to tables
      * Set to 0.0 when stopping or turning
    
    - Angular velocity: -1.5 to 1.5 rad/s
      * Maximum change: 0.3 rad/s per update
      * Use 0.2-0.5 rad/s for scanning
      * For pivot turns, set linear_velocity to 0.0

    CRITICAL SAFETY RULES:
    1. MUST STOP (linear_velocity = 0.0) when:
       - Any object is within 1.5 meters
       - A table surface is in full view for cataloging
    2. Prefix description with "STOP:" when stopping
    3. Only proceed forward when path is clear beyond 1.5m

    DESCRIPTION REQUIREMENTS:
    1. Always state current action AND next intended action
    2. When stopping to catalog, format as:
       "STOP: Cataloging table with [items]. Next: [pivot/search] for new tables"
    3. During movement, format as:
       "[Current action]. Next: [intended action]"
    4. Always include a detailed description of what you see in the image:
       - Describe the general scene layout
       - List any tables and their positions (left, right, center)
       - Identify and describe all visible objects
       - Note any potential obstacles or hazards
       - Estimate distances to key objects

    NAVIGATION STRATEGY:
    1. SEARCH PATTERN:
       - Rotate slowly in place (set linear_velocity=0.0, angular_velocity=0.5)
       - Continue rotating until a table is detected
    2. TABLE APPROACH:
       - When table detected, stop rotation
       - Turn to face table directly
       - Approach at reduced speed (0.2-0.4 m/s)
       - Stop when optimal viewing distance reached
    3. After cataloging:
       - Resume rotating search from current position"""

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
        # Update chat history max_messages to match history_length minus 1 (for new message)
        chat_history.max_messages = history_length - 1
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