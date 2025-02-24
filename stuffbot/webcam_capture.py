import cv2
import os
import threading
from datetime import datetime

class BufferlessVideoCapture:
    def __init__(self, name):
        self.cap = cv2.VideoCapture(name)
        # Set camera properties
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 15)
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        self.lock = threading.Lock()
        self.frame = None
        self.grabbed = False
        self.t = threading.Thread(target=self._reader)
        self.t.daemon = True
        self.t.start()

    def _reader(self):
        while True:
            with self.lock:
                self.grabbed, self.frame = self.cap.read()
            if not self.grabbed:
                break

    def read(self):
        with self.lock:
            frame = self.frame.copy() if self.frame is not None else None
            grabbed = self.grabbed
        return grabbed, frame

    def release(self):
        self.cap.release()

def main():
    # Initialize bufferless webcam
    cap = BufferlessVideoCapture(0)

    # Create images directory if it doesn't exist
    os.makedirs('images', exist_ok=True)

    print("Webcam Capture Tool")
    print("Press ENTER to capture a frame, or type 'q' to quit")

    try:
        while True:
            # Get the latest frame
            ret, frame = cap.read()
            
            if not ret:
                print("Error reading from webcam")
                break

            # Wait for user input (non-blocking)
            user_input = input().lower()
            
            # If 'q' entered, exit
            if user_input == 'q':
                break
                
            # If ENTER pressed (empty input), save frame
            if user_input == '':
                # Generate timestamp for unique filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                image_path = f"images/frame_{timestamp}.jpg"
                
                # Save frame
                cv2.imwrite(image_path, frame)
                print(f"Saved frame to {image_path}")

    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("Shutdown complete.")

if __name__ == "__main__":
    main() 