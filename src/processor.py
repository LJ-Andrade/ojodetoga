import cv2
import numpy as np
import imutils
import time
import argparse
from urllib.request import urlopen
import threading


class ESP32StreamProcessor:
    """Processor for ESP32CAM MJPEG stream with face and object detection."""
    
    def __init__(self, stream_url, confidence_threshold=0.5, headless=False):
        self.stream_url = stream_url
        self.confidence_threshold = confidence_threshold
        self.headless = headless
        
        # Load Haar Cascade for face detection (fast, built-in)
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        # Load MobileNet SSD for object detection (lightweight)
        self._load_object_detector()
        
        # Class labels for MobileNet SSD
        self.classes = ["background", "aeroplane", "bicycle", "bird", "boat",
                       "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
                       "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
                       "sofa", "train", "tvmonitor"]
        
        # Colors for visualization
        self.colors = np.random.uniform(0, 255, size=(len(self.classes), 3))
        
    def _load_object_detector(self):
        """Load MobileNet SSD model (downloads if not present)."""
        model_file = "MobileNetSSD_deploy.caffemodel"
        config_file = "MobileNetSSD_deploy.prototxt"
        
        # Model URLs
        model_url = "https://github.com/chuanqi305/MobileNet-SSD/raw/master/mobilenet_iter_73000.caffemodel"
        config_url = "https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/deploy.prototxt"
        
        import os
        if not os.path.exists(model_file):
            print(f"Downloading {model_file}...")
            import urllib.request
            urllib.request.urlretrieve(model_url, model_file)
            print("Download complete!")
            
        if not os.path.exists(config_file):
            print(f"Downloading {config_file}...")
            import urllib.request
            urllib.request.urlretrieve(config_url, config_file)
            print("Download complete!")
        
        self.net = cv2.dnn.readNetFromCaffe(config_file, model_file)
        
    def detect_faces(self, frame):
        """Detect faces using Haar Cascade."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.1, 
            minNeighbors=5, 
            minSize=(30, 30)
        )
        return faces
    
    def detect_objects(self, frame):
        """Detect objects using MobileNet SSD."""
        (h, w) = frame.shape[:2]
        
        # Create blob from image
        blob = cv2.dnn.blobFromImage(
            cv2.resize(frame, (300, 300)), 
            0.007843, 
            (300, 300), 
            127.5
        )
        
        # Pass blob through network
        self.net.setInput(blob)
        detections = self.net.forward()
        
        objects = []
        for i in np.arange(0, detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            
            if confidence > self.confidence_threshold:
                idx = int(detections[0, 0, i, 1])
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype("int")
                
                objects.append({
                    'class': self.classes[idx],
                    'confidence': confidence,
                    'box': (startX, startY, endX, endY)
                })
                
        return objects
    
    def draw_detections(self, frame, faces, objects):
        """Draw bounding boxes for faces and objects."""
        # Draw faces (green boxes)
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, "Face", (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Draw objects (colored boxes)
        for obj in objects:
            (startX, startY, endX, endY) = obj['box']
            label = f"{obj['class']}: {obj['confidence']:.2f}"
            idx = self.classes.index(obj['class'])
            color = self.colors[idx]
            
            cv2.rectangle(frame, (startX, startY), (endX, endY), color, 2)
            y = startY - 15 if startY - 15 > 15 else startY + 15
            cv2.putText(frame, label, (startX, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return frame
    
    def _capture_frame(self, capture_url):
        """Capture a single frame from ESP32CAM."""
        try:
            resp = urlopen(capture_url, timeout=5)
            img_array = np.array(bytearray(resp.read()), dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            return frame
        except Exception as e:
            return None
    
    def process_stream(self):
        """Main processing loop for ESP32CAM stream."""
        print(f"Connecting to ESP32CAM at {self.stream_url}...")
        
        # Detect if we should use capture mode (frame-by-frame) or stream mode
        # Always use the provided URL
        capture_url = self.stream_url
        # Test if the URL supports streaming, otherwise use capture mode
        use_capture_mode = not self._test_stream()
        
        if use_capture_mode:
            print("📷 Using CAPTURE mode (frame-by-frame)")
        else:
            print("🎥 Using STREAM mode (MJPEG)")
        
        if self.headless:
            print("Running in HEADLESS mode (no GUI)")
            print("Press Ctrl+C to quit")
        else:
            print("Press 'q' to quit")
        
        fps_counter = 0
        fps = 0
        frame_count = 0
        start_time = time.time()
        last_log_time = time.time()
        
        try:
            if use_capture_mode:
                # Capture mode: poll frames every ~100ms
                while True:
                    frame = self._capture_frame(capture_url)
                    
                    if frame is None:
                        time.sleep(0.1)
                        continue
                    
                    frame_count += 1
                    
                    # Process frame
                    frame, faces, objects = self._process_frame(frame)
                    
                    # Calculate FPS
                    fps_counter += 1
                    elapsed_time = time.time() - start_time
                    if elapsed_time > 1.0:
                        fps = fps_counter / elapsed_time
                        fps_counter = 0
                        start_time = time.time()
                    
                    # Log or display
                    if self.headless:
                        if time.time() - last_log_time > 2.0:
                            self._log_detections(frame_count, fps, faces, objects)
                            last_log_time = time.time()
                    else:
                        cv2.imshow("ESP32CAM - Face & Object Detection", frame)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            break
                    
                    # Small delay to not overwhelm the ESP32
                    time.sleep(0.05)
            else:
                # Stream mode: MJPEG continuous stream
                stream = urlopen(self.stream_url)
                bytes_buffer = bytes()
                
                while True:
                    try:
                        bytes_buffer += stream.read(1024)
                        a = bytes_buffer.find(b'\xff\xd8')
                        b = bytes_buffer.find(b'\xff\xd9')
                        
                        if a != -1 and b != -1:
                            jpg = bytes_buffer[a:b+2]
                            bytes_buffer = bytes_buffer[b+2:]
                            
                            frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                            
                            if frame is None:
                                continue
                            
                            frame_count += 1
                            frame, faces, objects = self._process_frame(frame)
                            
                            # Calculate FPS
                            fps_counter += 1
                            elapsed_time = time.time() - start_time
                            if elapsed_time > 1.0:
                                fps = fps_counter / elapsed_time
                                fps_counter = 0
                                start_time = time.time()
                            
                            # Log or display
                            if self.headless:
                                if time.time() - last_log_time > 2.0:
                                    self._log_detections(frame_count, fps, faces, objects)
                                    last_log_time = time.time()
                            else:
                                cv2.imshow("ESP32CAM - Face & Object Detection", frame)
                                if cv2.waitKey(1) & 0xFF == ord('q'):
                                    break
                                    
                    except Exception as e:
                        if not self.headless:
                            print(f"Error: {e}")
                        continue
                
                stream.close()
                    
        except KeyboardInterrupt:
            print("\n👋 Stopping...")
        
        if not self.headless:
            cv2.destroyAllWindows()
        print(f"Stream closed. Processed {frame_count} frames.")
    
    def _test_stream(self):
        """Test if stream mode is available."""
        try:
            # Try to read a bit from the stream
            stream = urlopen(self.stream_url, timeout=3)
            data = stream.read(1024)
            stream.close()
            # Check if it looks like JPEG data
            return b'\xff\xd8' in data
        except:
            return False
    
    def _process_frame(self, frame):
        """Process a single frame: detect and draw."""
        # Resize for faster processing
        frame = imutils.resize(frame, width=640)
        
        # Detect faces
        faces = self.detect_faces(frame)
        
        # Detect objects
        objects = self.detect_objects(frame)
        
        # Draw detections (only if not headless, or always draw but don't show)
        frame = self.draw_detections(frame, faces, objects)
        
        return frame, faces, objects
    
    def _log_detections(self, frame_count, fps, faces, objects):
        """Log detections to console in headless mode."""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] Frame #{frame_count} | FPS: {fps:.1f} | Faces: {len(faces)} | Objects: {len(objects)}")
        
        if len(faces) > 0:
            print(f"  👤 Faces detected: {len(faces)}")
            
        if len(objects) > 0:
            for obj in objects:
                print(f"  📦 {obj['class']} ({obj['confidence']:.2f})")


def main():
    parser = argparse.ArgumentParser(description='ESP32CAM Stream Processor')
    parser.add_argument('--url', default='http://192.168.1.48/',
                       help='ESP32CAM stream URL (default: http://192.168.1.48/)')
    parser.add_argument('--confidence', type=float, default=0.5,
                       help='Minimum confidence for object detection (default: 0.5)')
    parser.add_argument('--headless', action='store_true',
                       help='Run without GUI (for servers/SSH)')
    
    args = parser.parse_args()
    
    processor = ESP32StreamProcessor(args.url, args.confidence, args.headless)
    processor.process_stream()


if __name__ == "__main__":
    main()
