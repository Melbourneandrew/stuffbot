import os
import uuid
from typing import Tuple
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

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