import cv2
from ultralytics import YOLO
import uuid
import os
import datetime

class ObjectTracker:
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
        """Initialize StuffBot with YOLO model and webcam"""
        self.model = YOLO(model_path)
        self.camera = cv2.VideoCapture(0)
        
        # Set camera resolution explicitly
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Verify the actual resolution being used
        actual_width = self.camera.get(cv2.CAP_PROP_FRAME_WIDTH)
        actual_height = self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT)
        print(f"Camera resolution: {actual_width}x{actual_height}")
        
        self.display_enabled = display_enabled
        self.tracked_objects = {}
        self.next_id = 1
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

    def process_frame(self):
        """Process a single frame from the webcam"""
        success, frame = self.camera.read()
        if not success:
            return None, []

        # Save vanilla frame only if save_images is True
        if self.save_images:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            vanilla_filename = f"image_{timestamp}.jpg"
            cv2.imwrite(os.path.join(self.output_dir, vanilla_filename), frame)

        # Run YOLOv8 inference with confidence threshold
        results = self.model(frame, conf=self.conf_threshold)
        
        # Create a separate frame for display
        display_frame = frame.copy() if self.display_enabled else None
        
        detections = []
        
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
            
            # Save detection images only if save_images is True
            if self.save_images:
                full_image, cropped_image = self.save_detection_images(
                    frame.copy(),
                    [x1, y1, x2, y2], 
                    class_name, 
                    object_id
                )
            else:
                full_image, cropped_image = None, None
            
            detections.append({
                'class_name': class_name,
                'object_id': object_id,
                'confidence': conf,
                'box': [x1, y1, x2, y2],
                'full_image': full_image,
                'cropped_image': cropped_image
            })
            
            # Display if enabled
            if self.display_enabled:
                cv2.rectangle(display_frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                cv2.putText(display_frame, f"{class_name} {object_id}", (int(x1), int(y1) - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        return display_frame if self.display_enabled else frame, detections

    def toggle_display(self):
        """Toggle the display on/off"""
        self.display_enabled = not self.display_enabled

def StuffBot_Detect(conf_threshold=0.5, save_images=True):
    """Function to be called from StuffBot_manual.py"""
    # Use singleton pattern to maintain one camera instance
    tracker = ObjectTracker.get_instance(
        conf_threshold=conf_threshold, 
        save_images=save_images
    )
    
    try:
        _, detections = tracker.process_frame()
        return detections
    except Exception as e:
        print(f"Error in object detection: {e}")
        return []

if __name__ == "__main__":
    # Test the script independently
    detections = StuffBot_Detect()
    for detection in detections:
        print(f"Detected {detection['class_name']} with ID {detection['object_id']}") 