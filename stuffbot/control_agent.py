from pydantic import BaseModel
from openai import OpenAI
import base64
import os
from prompts import RobotMode, MovementCommand, get_system_prompt, get_mode_prompt

class RobotState(BaseModel):
    current_linear_velocity: float
    current_angular_velocity: float

class ControlAgent:
    def __init__(self):
        self.current_mode = RobotMode.LOOK_FOR_TABLE
        self.chat_history = ChatHistory()
        # self.client = OpenAI()
        self.client = OpenAI(
            api_key=os.getenv("GEMINI_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )
        self.model_name = "gemini-2.0-flash-lite-preview-02-05"

    def get_movement_command(self, image_data, robot_state: RobotState, is_path=False, history_length=1) -> MovementCommand:
        # Handle both file paths and image bytes
        if is_path:
            base64_image = encode_image(image_data)
        else:
            base64_image = encode_image_bytes(image_data)

        # Get the base system prompt and the current state-specific prompt
        system_prompt = get_system_prompt() + "\n\n" + get_mode_prompt(self.current_mode)

        user_content = [
            {
                "type": "text",
                "text": f"""Current robot state:
                - Linear velocity: {robot_state.current_linear_velocity:.2f} m/s
                - Angular velocity: {robot_state.current_angular_velocity:.2f} rad/s
                - Current mode: {self.current_mode.name}

                Analyze this image and provide updated movement commands for the robot based on the current mode.
                Follow the mode-specific objectives and transition rules."""
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
            self.chat_history.max_messages = history_length
            messages = self.chat_history.get_messages_for_prompt(system_prompt, user_content)
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]

        completion = self.client.beta.chat.completions.parse(
            model=self.model_name,
            messages=messages,
            response_format=MovementCommand,
            max_tokens=1000,
        )

        # Get the parsed response
        movement_command = completion.choices[0].message.parsed
        
        # Update the mode based on the LLM's decision
        self.current_mode = movement_command.next_mode
        
        self.chat_history.add_exchange(system_prompt, user_content, movement_command)
        
        return movement_command

class ChatHistory:
    def __init__(self, max_messages=3):
        self.max_messages = max_messages
        self.messages = []

    def add_exchange(self, system_prompt, user_content, assistant_response):
        # Convert MovementCommand to dict for better serialization
        assistant_dict = {
            "linear_velocity": assistant_response.linear_velocity,
            "angular_velocity": assistant_response.angular_velocity,
            "description": assistant_response.description,
            "next_mode": assistant_response.next_mode.name
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
                f.write(f"Assistant: Mode={msg['assistant']['next_mode']}, {str(msg['assistant'])[:150]}...\n\n")

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def encode_image_bytes(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')