import cv2
import numpy as np

class DistanceDetector:
    def __init__(self, known_width=0.15):  # default known_width in meters (e.g., 15cm)
        """
        Initialize the distance detector
        known_width: The real-world width of reference object in meters
        """
        # Approximate focal length for typical webcam (can be calibrated for better accuracy)
        self.focal_length = 800  # pixels
        self.known_width = known_width

    def estimate_distance(self, pixel_width):
        """
        Estimate distance using the formula: Distance = (Known Width × Focal Length) / Pixel Width
        pixel_width: width of object in pixels
        Returns: distance in meters
        """
        try:
            if pixel_width == 0:
                return 0
            
            distance = (self.known_width * self.focal_length) / pixel_width
            return round(distance, 2)
        except Exception as e:
            print(f"Error estimating distance: {e}")
            return 0

    def calculate_object_distance(self, box):
        """
        Calculate distance based on bounding box
        box: [x1, y1, x2, y2] coordinates or array-like object
        Returns: estimated distance in meters
        """
        try:
            # Handle different input types
            if isinstance(box, (list, tuple, np.ndarray)):
                # Ensure we have at least 4 values
                if len(box) >= 4:
                    # Calculate width of object in pixels
                    pixel_width = abs(float(box[2]) - float(box[0]))
                    return self.estimate_distance(pixel_width)
            print(f"Invalid box format: {box}")
            return 0
        except Exception as e:
            print(f"Error calculating distance: {e}")
            return 0

def calibrate_focal_length(known_distance, known_width, pixel_width):
    """
    Calibrate the focal length using a reference object
    known_distance: actual distance to object in meters
    known_width: actual width of object in meters
    pixel_width: width of object in pixels
    Returns: focal length in pixels
    """
    try:
        # Focal Length = (Pixel Width × Known Distance) / Known Width
        focal_length = (pixel_width * known_distance) / known_width
        return focal_length
    except Exception as e:
        print(f"Error calibrating focal length: {e}")
        return 800  # Return default focal length

if __name__ == "__main__":
    # Example usage
    detector = DistanceDetector()
    
    # Example bounding box [x1, y1, x2, y2]
    sample_box = [100, 100, 200, 200]
    distance = detector.calculate_object_distance(sample_box)
    print(f"Estimated distance: {distance} meters") 