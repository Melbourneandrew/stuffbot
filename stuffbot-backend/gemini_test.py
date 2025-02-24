from pydantic import BaseModel
from openai import OpenAI
from typing import List
import base64
import time

# Initialize OpenAI client
client = OpenAI(
    api_key="AIzaSyAxuLbHGAlB7gE-MqSEgywFvWOGQMmWZio",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

model_name = "gemini-2.0-flash-lite-preview-02-05"

# Define the structure we want to extract from the image
class ImageAnalysis(BaseModel):
    main_subject: str
    colors: List[str]
    objects: List[str]
    scene_description: str
    api_duration: float = 0.0  # Add field to store API call duration

# Function to analyze image
def analyze_image(image_path: str) -> ImageAnalysis:
    # Read image file as base64
    with open(image_path, "rb") as image_file:
        # Create message with image
        messages = [
            {
                "role": "system",
                "content": "Extract structured information about the image."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Analyze this image and provide structured information about the main subject, colors present, objects visible, and a brief scene description."
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(image_file.read()).decode()}"}
                    }
                ]
            }
        ]

        # Time the API call specifically
        start_time = time.time()
        completion = client.beta.chat.completions.parse(
            model=model_name,
            messages=messages,
            response_format=ImageAnalysis,
        )
        end_time = time.time()
        api_duration = end_time - start_time

        result = completion.choices[0].message.parsed
        result.api_duration = api_duration  # Add duration to the result
        return result

# Example usage
if __name__ == "__main__":
    image_paths = [
        "stuff_test_images/stuff_all.png",
        "stuff_test_images/stuff_caliper.png",
        "stuff_test_images/stuff_watch.png",
        "stuff_test_images/stuff_headphones.png"
    ]
    
    times = []
    analyses = []
    
    for path in image_paths:
        start_time = time.time()
        analysis = analyze_image(path)
        end_time = time.time()
        times.append(end_time - start_time)
        analyses.append(analysis)
    
    # Print results for first analysis
    print(f"Main subject: {analyses[0].main_subject}")
    print(f"Colors: {', '.join(analyses[0].colors)}")
    print(f"Objects: {', '.join(analyses[0].objects)}")
    print(f"Scene description: {analyses[0].scene_description}")
    
    # Print timing results
    print("\nTiming Results (API calls only):")
    for i, (path, analysis) in enumerate(zip(image_paths, analyses)):
        print(f"Image {i+1} ({path.split('/')[-1]}): {analysis.api_duration:.2f} seconds")
    print(f"Total API time: {sum(a.api_duration for a in analyses):.2f} seconds")
