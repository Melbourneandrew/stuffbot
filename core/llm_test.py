from pydantic import BaseModel
from openai import OpenAI
import base64

class MovementCommand(BaseModel):
    linear_velocity: float  # meters per second
    angular_velocity: float  # radians per second
    duration: float  # seconds
    description: str

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
    2. Do not issue forward movement commands until a water bottle is positively identified
    3. If collision risk detected, immediately STOP:
       - Set both linear_velocity and angular_velocity to 0.0
       - Use brief duration (0.1-0.5 seconds)
       - Include "STOP: Collision Risk" in description

    MOVEMENT GUIDELINES:
    1. Linear Velocity:
       - Range: -1.0 to 1.0 m/s
       - Must be 0.0 during all turning and scanning operations
       - Only use forward motion after water bottle confirmation
    
    2. Angular Velocity:
       - Range: -1.5 to 1.5 rad/s
       - Use 0.2-0.5 rad/s for careful scanning
       - Precise control for hairpin turns

    SEARCH PROTOCOL (When water bottle not visible):
    1. Execute systematic scanning pattern
    2. Maintain 0.0 m/s linear velocity
    3. Use slow angular velocity (0.2-0.5 rad/s)
    4. Scan methodically to cover all areas

    ENVIRONMENTAL ANALYSIS:
    Before each movement, evaluate:
    - Precise distance estimates to visible objects (in meters)
    - Potential obstacles or hazards
    - Required clearance for turns
    - Appropriate speeds based on environmental complexity

    OUTPUT FORMAT:
    Return movement commands as JSON:
    {
        "linear_velocity": float,  // Forward/backward speed in m/s
        "angular_velocity": float, // Turning speed in rad/s
        "duration": float,        // Movement duration in seconds
        "description": string     // Detailed explanation including observations
    }
    """

    user_prompt = f"""Analyze this image and provide movement commands for a robot to navigate the scene safely.
    Consider obstacles, required turns, and appropriate speeds for the environment."""

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        response_format=MovementCommand,
        max_tokens=1000,
    )

    # Get the parsed response directly
    movement_command = completion.choices[0].message.parsed
    
    return movement_command

# Example usage
if __name__ == "__main__":
    image_path = "path/to/your/image.jpg"
    try:
        movement = get_movement_command(image_path)
        print(f"Linear Velocity: {movement.linear_velocity} m/s")
        print(f"Angular Velocity: {movement.angular_velocity} rad/s")
        print(f"Duration: {movement.duration} s")
        print(f"Description: {movement.description}")
    except Exception as e:
        print(f"Error processing image: {e}")