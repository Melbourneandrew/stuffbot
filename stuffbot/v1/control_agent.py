from pydantic import BaseModel
from openai import OpenAI
import base64

class MovementCommand(BaseModel):
    linear_velocity: float  # meters per second
    angular_velocity: float  # radians per second
    duration: float  # seconds
    description: str

class ChatHistory:
    def __init__(self, max_messages=3):
        self.max_messages = max_messages
        self.messages = []

    def add_exchange(self, system_prompt, user_content, assistant_response):
        # Add the new exchange
        exchange = {
            "system": system_prompt,
            "user": user_content,
            "assistant": assistant_response
        }
        self.messages.append(exchange)
        
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

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def encode_image_bytes(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

def get_movement_command(image_data, is_path=False) -> MovementCommand:
    client = OpenAI()
    
    # Handle both file paths and image bytes
    if is_path:
        base64_image = encode_image(image_data)
    else:
        base64_image = encode_image_bytes(image_data)

    system_prompt = """You are a robot movement analyzer. You are controlling a compact robot with 2 hub motors capable of making precise hairpin turns. When given an image, carefully analyze the scene, estimate distances to objects, and provide movement commands for safe navigation.

    SAFETY PROTOCOLS:
    1. Safety is the highest priority - avoid any potential collisions
    2. Do not issue forward movement commands until a table surface is positively identified
    3. If collision risk detected, immediately STOP:
       - Set both linear_velocity and angular_velocity to 0.0
       - Use brief duration (0.1-0.5 seconds)
       - Include "STOP: Collision Risk" in description

    MOVEMENT GUIDELINES:
    1. Linear Velocity:
       - Range: -1.0 to 1.0 m/s
       - Must be 0.0 during all turning and scanning operations
       - Forward motion allowed only when approaching identified table
       - Slow approach (0.2-0.4 m/s) when nearing table
    
    2. Angular Velocity:
       - Range: -1.5 to 1.5 rad/s
       - Use 0.2-0.5 rad/s for careful scanning
       - Precise control for hairpin turns
       - All turning movements must be at least 1.0 seconds in duration

    SEARCH PROTOCOL (When table not visible):
    1. Execute systematic scanning pattern
    2. Maintain 0.0 m/s linear velocity
    3. Use slow angular velocity (0.2-0.5 rad/s)
    4. Scan methodically to cover all areas

    TABLE APPROACH PROTOCOL:
    1. When table spotted, approach slowly and directly
    2. Stop at optimal viewing distance (0.5-1.0 meters)
    3. Position for clear view of table surface
    4. Scan table surface methodically for items

    ENVIRONMENTAL ANALYSIS:
    Before each movement, evaluate:
    - Precise distance estimates to visible objects (in meters)
    - Potential obstacles or hazards
    - Required clearance for turns
    - Appropriate speeds based on environmental complexity
    - Table surface visibility and items present

    OUTPUT FORMAT:
    Return movement commands as JSON:
    {
        "linear_velocity": float,  // Forward/backward speed in m/s
        "angular_velocity": float, // Turning speed in rad/s
        "duration": float,        // Movement duration in seconds
        "description": string     // Detailed explanation including observations. Say "TABLE SURFACE SPOTTED" when a table is found. List all items visible on table surface.
    }
    """

    user_content = [
        {
            "type": "text",
            "text": """Analyze this image and provide movement commands for a robot to navigate the scene safely.
            Look for table surfaces and any items on them. If a table is found, approach it carefully for optimal viewing."""
        },
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
        }
    ]

    # Get messages including chat history
    messages = chat_history.get_messages_for_prompt(system_prompt, user_content)

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=messages,
        response_format=MovementCommand,
        max_tokens=1000,
    )

    # Get the parsed response
    movement_command = completion.choices[0].message.parsed
    
    # Add the exchange to chat history
    chat_history.add_exchange(system_prompt, user_content, movement_command)
    
    return movement_command