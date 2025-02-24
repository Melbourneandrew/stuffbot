import cv2
from ultralytics import YOLO
import uuid
import os
import datetime

class ImageProcessor:
    _instance = None
    
    @classmethod
    def get_instance(cls, **kwargs):
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        else:
            # Update existing instance parameters
            cls._instance.conf_threshold = kwargs.get('conf_threshold', 0.5)
            cls._instance.save_images = kwargs.get('save_images', True)
            if cls._instance.save_images:
                # Create new output directory for this detection run
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                cls._instance.output_dir = os.path.join("detected_objects", f"detection_run_{timestamp}")
                os.makedirs(cls._instance.output_dir, exist_ok=True)
        return cls._instance

    def __init__(self, model_path="yolov8n.pt", display_enabled=False, conf_threshold=0.5, save_images=True):
        """Initialize ImageProcessor with YOLO model"""
        self.model = YOLO(model_path)
        self.display_enabled = display_enabled
        self.tracked_objects = {}
        self.conf_threshold = conf_threshold
        self.save_images = save_images
        
        # Create output directory only if saving images
        if self.save_images:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self.output_dir = os.path.join("detected_objects", f"detection_run_{timestamp}")
            os.makedirs(self.output_dir, exist_ok=True)

    def generate_unique_id(self):
        """Generate a unique identifier for each detected object"""
        return str(uuid.uuid4())[:8]

    def save_detection_images(self, frame, box, class_name, object_id):
        """Save both the full frame with single box and cropped object"""
        frame_with_box = frame.copy()
        height, width = frame.shape[:2]
        
        # Add padding to the box (20 pixels on each side)
        padding = 20
        x1, y1, x2, y2 = map(int, box)
        
        # Ensure padded coordinates don't go outside frame boundaries
        x1_padded = max(0, x1 - padding)
        y1_padded = max(0, y1 - padding)
        x2_padded = min(width, x2 + padding)
        y2_padded = min(height, y2 + padding)
        
        # Draw the padded bounding box
        cv2.rectangle(frame_with_box, (x1_padded, y1_padded), (x2_padded, y2_padded), (0, 255, 0), 2)
        cv2.putText(frame_with_box, class_name,
                    (x1_padded, y1_padded - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Save full frame with only this box
        full_image_filename = f"{class_name}_{object_id}_full.jpg"
        cv2.imwrite(os.path.join(self.output_dir, full_image_filename), frame_with_box)
        
        # Crop using padded coordinates
        cropped = frame[y1_padded:y2_padded, x1_padded:x2_padded]
        cropped_filename = f"{class_name}_{object_id}_cropped.jpg"
        cv2.imwrite(os.path.join(self.output_dir, cropped_filename), cropped)
        
        return full_image_filename, cropped_filename

    def process_image(self, frame):
        """Process a provided image frame and return both full and cropped images"""
        if frame is None:
            return None, None, []

        # Run YOLOv8 inference with confidence threshold
        results = self.model(frame, conf=self.conf_threshold)
        
        # Create a separate frame for display
        display_frame = frame.copy() if self.display_enabled else None
        
        detections = []
        full_images = []
        cropped_images = []
        
        # Process each detection
        for result in results[0].boxes.data:
            x1, y1, x2, y2, conf, class_id = result
            class_name = self.model.names[int(class_id)]
            
            # Skip if the detected object is a person
            if class_name.lower() == 'person':
                continue
            
            # Generate or retrieve object ID
            detection_key = f"{class_name}_{int(x1)}_{int(y1)}"
            if detection_key not in self.tracked_objects:
                self.tracked_objects[detection_key] = self.generate_unique_id()
            object_id = self.tracked_objects[detection_key]
            
            # Skip if there's already a detection with this object_id
            if any(d['object_id'] == object_id for d in detections):
                continue
                
            # Create separate frames for this detection
            frame_with_single_box = frame.copy()
            height, width = frame.shape[:2]
            
            # Add padding to the box (20 pixels on each side)
            padding = 20
            x1_padded = max(0, int(x1) - padding)
            y1_padded = max(0, int(y1) - padding)
            x2_padded = min(width, int(x2) + padding)
            y2_padded = min(height, int(y2) + padding)
            
            # Draw box on single-detection frame
            cv2.rectangle(frame_with_single_box, (x1_padded, y1_padded), (x2_padded, y2_padded), (0, 255, 0), 2)
            cv2.putText(frame_with_single_box, class_name,
                        (x1_padded, y1_padded - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Create cropped image
            cropped_image = frame[y1_padded:y2_padded, x1_padded:x2_padded]
            
            # Add images to their respective lists
            full_images.append(frame_with_single_box)
            cropped_images.append(cropped_image)
            
            detections.append({
                'class_name': class_name,
                'object_id': object_id,
                'confidence': conf,
                'box': [x1, y1, x2, y2]
            })
            
            # Display if enabled
            if self.display_enabled:
                cv2.rectangle(display_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                cv2.putText(display_frame, f"{class_name} {object_id}", (int(x1), int(y1) - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        return full_images if full_images else None, cropped_images if cropped_images else None, detections

    def toggle_display(self):
        """Toggle the display on/off"""
        self.display_enabled = not self.display_enabled

def process_single_image(image_path, conf_threshold=0.5, save_images=True):
    """Function to process a single image file"""
    processor = ImageProcessor.get_instance(
        conf_threshold=conf_threshold,
        save_images=save_images,
        display_enabled=True
    )
    
    try:
        # Read the image
        frame = cv2.imread(image_path)
        if frame is None:
            raise ValueError(f"Could not read image at {image_path}")
            
        # Process the image
        display_frame, cropped_image, detections = processor.process_image(frame)
        
        # Display the frame with detections
        cv2.imshow('Object Detection', display_frame)
        cv2.waitKey(2000)  # Show image for 2 seconds
        cv2.destroyAllWindows()
        
        return detections
    except Exception as e:
        print(f"Error in image processing: {e}")
        return []

if __name__ == "__main__":
    # Test the script with a sample image
    test_image_path = "path/to/test/image.jpg"  # Replace with actual test image path
    detections = process_single_image(test_image_path)
    for detection in detections:
        print(f"Detected {detection['class_name']} with ID {detection['object_id']}") 