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

    def add_exchange(self, system_prompt, user_content, assistant_response):
        # Convert MovementCommand to dict for better serialization
        assistant_dict = {
            "linear_velocity": assistant_response.linear_velocity,
            "angular_velocity": assistant_response.angular_velocity,
            "description": assistant_response.description
        }

        # Add the new exchange
        exchange = {
            "system": system_prompt,
            "user": user_content,
            "assistant": assistant_dict
        }
        self.messages.append(exchange)

        self.save_history()
        
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

    def save_history(self):
        # Create histories directory if it doesn't exist
        os.makedirs("histories", exist_ok=True)
        
        # Find the next available file number
        i = 1
        while os.path.exists(f"histories/chat_history_{i}.txt"):
            i += 1
        
        filename = f"histories/chat_history_{i}.txt"
        
        with open(filename, "w") as f:
            # Write system prompt once if there are any messages
            if self.messages:
                f.write(f"System: {self.messages[0]['system'][:150]}...\n\n")
            
            # Write each exchange in order
            for msg in self.messages:
                f.write(f"User: {str(msg['user'])[:150]}...\n")
                f.write(f"Assistant: {str(msg['assistant'])[:150]}...\n\n")

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

    system_prompt = """You are controlling a robot to find and approach TABLES and DESKS.
    YOU LOVE TABLES AND DESKS.

    OBJECTIVE:
    1. Rotate to search for tables or desks
    2. When a table or desk is seen AT ALL, drive towards it. DO NOT INITIATE A TURN. Drive DIRECTLY towards the table or desk.
    3. STOP when close to table or desk (within 1.5m)
    
    MOVEMENT RULES:
    There are 3 types of movement:
    1. Going Straight (approaching table or desk)
        - Linear velocity: 0.5 m/s
        - Angular velocity: 0.0 rad/s
    
    2. Turning (searching for table)
        - Linear velocity: 0.0 m/s
        - Angular velocity: 0.5 rad/s
    
    3. Stopping (when close to table/desk or need complete stop)
        - Linear velocity: 0.0 m/s
        - Angular velocity: 0.0 rad/s

    Valid ranges (if needed):
    - Linear velocity: -1.0 to 1.0 m/s
    - Angular velocity: -1.5 to 1.5 rad/s

    DESCRIPTION FORMAT:
    Explain what you see and why you chose those velocities.
    Example: "Table or desk spotted on left - stopping rotation and beginning approach" or
            "No tables or desksvisible - continuing rotation to search" or
            "Table or desk within 1.5m - stopping all movement"
    """

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
        # Set the max_messages to match history_length
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