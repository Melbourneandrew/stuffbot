from supabase import create_client
from typing import Tuple

def clear_stuff_bucket(supabase_client) -> Tuple[bool, str]:
    """
    Clears all images from the stuff_images_bucket in both 'full' and 'partial' folders.
    
    Args:
        supabase_client: Initialized Supabase client
        
    Returns:
        Tuple[bool, str]: (success, error_message)
    """
    print("Clearing stuff bucket")
    try:
        # List all files in the bucket
        response = supabase_client.storage.from_('stuff_images_bucket').list()
        file_names = [file['name'] for file in response]
        
        # Delete all files if any exist
        if file_names:
            supabase_client.storage.from_('stuff_images_bucket').remove(file_names)
            print(f"Deleted {len(file_names)} files")
        else:
            print("Bucket is already empty")
            
        return True, ""
        
    except Exception as e:
        return False, str(e)
