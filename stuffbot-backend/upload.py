from supabase import create_client
import os
from typing import Tuple
import time
from clear_bucket import clear_stuff_bucket
import uuid  # Add this import at the top
from PIL import Image  # Add this import at the top
import io  # Add this import for BytesIO
import PIL

# List of test cases - you can fill these in
test_cases = [
    {
        "full_image": "book_55fec87e_full.jpg",
        "partial_image": "book_55fec87e_cropped.jpg"
    },
    {
        "full_image": "book_58df37c8_full.jpg",
        "partial_image": "book_58df37c8_cropped.jpg"
    },
    {
        "full_image": "bottle_370d7e47_full.jpg",
        "partial_image": "bottle_370d7e47_cropped.jpg"
    },
    {
        "full_image": "bottle_50ccb018_full.jpg",
        "partial_image": "bottle_50ccb018_cropped.jpg"
    },
    {
        "full_image": "bowl_ef864a02_full.jpg",
        "partial_image": "bowl_ef864a02_cropped.jpg"
    },
    {
        "full_image": "cell phone_7abc4614_full.jpg",
        "partial_image": "cell phone_7abc4614_cropped.jpg"
    },
    {
        "full_image": "chair_1714ab3e_full.jpg",
        "partial_image": "chair_1714ab3e_cropped.jpg"
    },
    {
        "full_image": "keyboard_cfbfb613_full.jpg",
        "partial_image": "keyboard_cfbfb613_cropped.jpg"
    },
    {
        "full_image": "laptop_f3a3585e_full.jpg",
        "partial_image": "laptop_f3a3585e_cropped.jpg"
    },
    {
        "full_image": "mouse_6d48acd3_full.jpg",
        "partial_image": "mouse_6d48acd3_cropped.jpg"
    },
    {
        "full_image": "remote_7de1710c_full.jpg",
        "partial_image": "remote_7de1710c_cropped.jpg"
    }
]

def upload_stuff_images(
    supabase_client,
    full_image_path: str,
    partial_image_path: str,
) -> Tuple[bool, str]:
    try:
        # Check if files exist
        if not os.path.exists(full_image_path) or not os.path.exists(partial_image_path):
            return False, f"Image files not found: {full_image_path} and/or {partial_image_path}"

        # Generate unique IDs for the images
        full_image_id = f"{uuid.uuid4()}.png"
        partial_image_id = f"{uuid.uuid4()}.png"
        
        # Upload full image
        with open(full_image_path, 'rb') as f:
            supabase_client.storage.from_('stuff_images_bucket').upload(
                full_image_id,
                f.read(),
                file_options={"content-type": "image/png"}
            )
        print("Full image uploaded")
        
        # Upload partial image
        with open(partial_image_path, 'rb') as f:
            supabase_client.storage.from_('stuff_images_bucket').upload(
                partial_image_id,
                f.read(),
                file_options={"content-type": "image/png"}
            )
        print("Partial image uploaded")
        # Insert record into stuff table
        data = {
            "full_image_id": full_image_id,
            "partial_image_id": partial_image_id,
            "class": "unknown",
            "approximate_price": 0.00,
            "location_description": "unknown"
        }
        print(data)
        result = supabase_client.table('stuff').insert(data).execute()
        print(f"Insert result: {result}")
        return True, ""
        
    except Exception as e:
        return False, str(e)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0")

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Directory containing test images
TEST_IMAGES_DIR = "stuff_test_images"

def process_test_images():
    # Clear the bucket before starting
    success, error = clear_stuff_bucket(supabase)
    if not success:
        print(f"Failed to clear bucket: {error}")
        return

    # Create a temporary directory for resized images
    temp_dir = "temp_resized_images"
    os.makedirs(temp_dir, exist_ok=True)

    # Add debug prints
    print(f"Current working directory: {os.getcwd()}")
    print(f"Looking for images in: {os.path.abspath(TEST_IMAGES_DIR)}")
    print(f"Directory contents: {os.listdir('.')}")
    if os.path.exists(TEST_IMAGES_DIR):
        print(f"Test images directory contents: {os.listdir(TEST_IMAGES_DIR)}")
    else:
        print(f"Test images directory '{TEST_IMAGES_DIR}' not found!")

    for case in test_cases:
        original_full_path = os.path.join(TEST_IMAGES_DIR, case["full_image"])
        partial_image_path = os.path.join(TEST_IMAGES_DIR, case["partial_image"])
        
        # Resize full image
        resized_full_path = os.path.join(temp_dir, f"resized_{case['full_image']}")
        with Image.open(original_full_path) as img:
            # Resize maintaining aspect ratio to 720p
            max_size = (1280, 720)  # Standard 720p resolution
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(resized_full_path, "PNG", optimize=True)
        
        # Add debug prints for specific files
        print(f"\nChecking paths:")
        print(f"Full image path: {resized_full_path} (exists: {os.path.exists(resized_full_path)})")
        print(f"Partial image path: {partial_image_path} (exists: {os.path.exists(partial_image_path)})")

        success, error = upload_stuff_images(
            supabase,
            resized_full_path,
            partial_image_path
        )

        if success:
            print(f"Successfully uploaded images: {resized_full_path} and {partial_image_path}")
        else:
            print(f"Failed to upload images: {resized_full_path} and {partial_image_path}")
            print(f"Error: {error}")

    # Clean up temporary directory
    import shutil
    shutil.rmtree(temp_dir)

if __name__ == "__main__":
    process_test_images()
