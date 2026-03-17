import cv2
import numpy as np
import imutils
import time
import threading
import queue
from urllib.request import urlopen
import base64


class StreamProcessor:
    """Processor for ESP32CAM/Webcam stream with adjustable parameters."""
    
    def __init__(self, stream_url, socketio=None, camera_mode='auto'):
        self.stream_url = stream_url
        self.socketio = socketio
        self.camera_mode = camera_mode  # 'auto', 'stream', or 'capture'
        
        # Adjustable parameters
        self.confidence_threshold = 0.5
        self.face_scale_factor = 1.1
        self.face_min_neighbors = 5
        self.frame_width = 640
        self.target_fps = 15  # Default target FPS (controls delay between frames)
        
        # Detection toggles
        self.enable_face_detection = True
        self.enable_object_detection = True
        
        # State
        self.is_running = False
        self.frame_count = 0
        self.fps = 0
        self.current_faces = []
        self.current_objects = []
        
        # Threading
        self.thread = None
        self.frame_queue = queue.Queue(maxsize=2)
        
        # Load models
        self._load_models()
        
    def _load_models(self):
        """Load detection models."""
        # Haar Cascade for face detection
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        # MobileNet SSD for object detection
        model_file = "MobileNetSSD_deploy.caffemodel"
        config_file = "MobileNetSSD_deploy.prototxt"
        
        import os
        import urllib.request
        
        if not os.path.exists(model_file):
            print(f"Downloading {model_file}...")
            urllib.request.urlretrieve(
                "https://github.com/chuanqi305/MobileNet-SSD/raw/master/mobilenet_iter_73000.caffemodel",
                model_file
            )
            
        if not os.path.exists(config_file):
            print(f"Downloading {config_file}...")
            urllib.request.urlretrieve(
                "https://raw.githubusercontent.com/chuanqi305/MobileNet-SSD/master/deploy.prototxt",
                config_file
            )
        
        self.net = cv2.dnn.readNetFromCaffe(config_file, model_file)
        
        self.classes = ["background", "aeroplane", "bicycle", "bird", "boat",
                       "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
                       "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
                       "sofa", "train", "tvmonitor"]
        self.colors = np.random.uniform(0, 255, size=(len(self.classes), 3))
        
    def detect_faces(self, frame):
        """Detect faces with current parameters."""
        if not self.enable_face_detection:
            return []
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=self.face_scale_factor,
            minNeighbors=self.face_min_neighbors,
            minSize=(30, 30)
        )
        return faces
    
    def detect_objects(self, frame):
        """Detect objects with current confidence threshold."""
        if not self.enable_object_detection:
            return []
        
        (h, w) = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(
            cv2.resize(frame, (300, 300)),
            0.007843,
            (300, 300),
            127.5
        )
        
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
                    'confidence': float(confidence),
                    'box': (int(startX), int(startY), int(endX), int(endY))
                })
        return objects
    
    def draw_detections(self, frame, faces, objects):
        """Draw bounding boxes."""
        # Draw faces (green)
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, "Face", (x, y-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Draw objects
        for obj in objects:
            (startX, startY, endX, endY) = obj['box']
            label = f"{obj['class']}: {obj['confidence']:.2f}"
            idx = self.classes.index(obj['class'])
            color = tuple(map(int, self.colors[idx]))
            
            cv2.rectangle(frame, (startX, startY), (endX, endY), color, 2)
            y = startY - 15 if startY - 15 > 15 else startY + 15
            cv2.putText(frame, label, (startX, y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return frame
    
    def _capture_frame(self):
        """Capture single frame."""
        try:
            # Special case: /capture endpoint always uses single-shot mode
            # even if stream mode is selected (ESP32CAM quirk)
            if '/capture' in self.stream_url.lower():
                return self._read_capture_frame()
            
            # Special case: /video endpoint is typically a stream (IP Webcam apps)
            # even if capture mode is selected
            if '/video' in self.stream_url.lower():
                return self._read_stream_frame()
            
            # Determine mode based on camera_mode setting
            if self.camera_mode == 'stream':
                # Force stream mode (ESP32CAM)
                return self._read_stream_frame()
            elif self.camera_mode == 'capture':
                # Force capture mode (Webcam IP)
                return self._read_capture_frame()
            else:
                # Auto-detect mode
                if 'stream' in self.stream_url or self._test_stream():
                    return self._read_stream_frame()
                else:
                    return self._read_capture_frame()
        except Exception as e:
            return None
    
    def _read_capture_frame(self):
        """Read single frame from capture endpoint (ESP32CAM /capture)."""
        try:
            resp = urlopen(self.stream_url, timeout=5)
            img_array = np.array(bytearray(resp.read()), dtype=np.uint8)
            resp.close()
            return cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        except Exception as e:
            return None
    
    def _read_stream_frame(self):
        """Read frame from MJPEG stream."""
        try:
            if not hasattr(self, '_stream'):
                print(f"Connecting to MJPEG stream: {self.stream_url}")
                self._stream = urlopen(self.stream_url, timeout=10)
                self._buffer = bytes()
                self._boundary = None
            
            max_attempts = 100
            attempts = 0
            
            while attempts < max_attempts:
                attempts += 1
                
                # Read more data
                if len(self._buffer) < 100000:
                    try:
                        chunk = self._stream.read(16384)
                        if not chunk:
                            break
                        self._buffer += chunk
                    except:
                        break
                
                # Try to detect boundary from stream data
                if self._boundary is None:
                    # Look for boundary pattern: --[boundary]\r\n
                    # Common patterns: --boundary, --Ba4oTv..., etc.
                    boundary_match = None
                    
                    # Try to find boundary from multipart content
                    if b'--' in self._buffer[:1000]:
                        # Find first occurrence of -- followed by characters and \r\n
                        import re
                        match = re.search(b'--([a-zA-Z0-9]+)\r\n', self._buffer[:2000])
                        if match:
                            self._boundary = match.group(1).decode('utf-8')
                            print(f"Detected boundary: {self._boundary}")
                    
                    # Alternative: Check HTTP headers for boundary
                    if self._boundary is None and b'Content-Type:' in self._buffer[:2000]:
                        header_part = self._buffer[:2000].decode('utf-8', errors='ignore')
                        if 'boundary=' in header_part:
                            import re
                            boundary_match = re.search(r'boundary=([^\r\n]+)', header_part)
                            if boundary_match:
                                self._boundary = boundary_match.group(1).strip()
                                print(f"Detected boundary from header: {self._boundary}")
                
                # If we have a boundary (multipart format), use it
                if self._boundary:
                    boundary_bytes = f'--{self._boundary}'.encode()
                    
                    # Find boundary in buffer
                    pos = 0
                    while pos < len(self._buffer):
                        boundary_pos = self._buffer.find(boundary_bytes, pos)
                        if boundary_pos == -1:
                            break
                        
                        # Find next boundary
                        next_boundary = self._buffer.find(boundary_bytes, boundary_pos + len(boundary_bytes))
                        if next_boundary == -1:
                            # Need more data
                            break
                        
                        # Extract frame between boundaries
                        frame_section = self._buffer[boundary_pos:next_boundary]
                        
                        # Find JPEG start (\xff\xd8) in frame section
                        jpeg_start = frame_section.find(b'\xff\xd8')
                        jpeg_end = frame_section.find(b'\xff\xd9')
                        
                        if jpeg_start != -1 and jpeg_end != -1 and jpeg_end > jpeg_start:
                            jpg = frame_section[jpeg_start:jpeg_end+2]
                            self._buffer = self._buffer[next_boundary:]
                            
                            frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                            if frame is not None:
                                return frame
                        
                        pos = next_boundary
                else:
                    # Standard MJPEG format (no multipart)
                    a = self._buffer.find(b'\xff\xd8')
                    b = self._buffer.find(b'\xff\xd9')
                    
                    if a != -1 and b != -1 and b > a:
                        jpg = self._buffer[a:b+2]
                        self._buffer = self._buffer[b+2:]
                        
                        frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                        if frame is not None:
                            return frame
                
                # Clean up buffer if too large
                if len(self._buffer) > 500000:
                    self._buffer = self._buffer[-200000:]
                    
            print(f"Stream warning: Could not find valid frame after {attempts} attempts")
            return None
            
        except Exception as e:
            print(f"Stream error: {e}")
            if hasattr(self, '_stream'):
                try:
                    self._stream.close()
                except:
                    pass
                delattr(self, '_stream')
            return None
    
    def _test_stream(self):
        """Test if URL is a stream."""
        try:
            resp = urlopen(self.stream_url, timeout=3)
            data = resp.read(2048)
            resp.close()
            return b'\xff\xd8' in data
        except:
            return False
    
    def _processing_loop(self):
        """Main processing loop."""
        fps_counter = 0
        fps_start_time = time.time()
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        while self.is_running:
            frame_start_time = time.time()
            
            frame = self._capture_frame()
            
            if frame is None:
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    print(f"Too many errors ({consecutive_errors}), reconnecting...")
                    # Force reconnection
                    if hasattr(self, '_stream'):
                        try:
                            self._stream.close()
                        except:
                            pass
                        delattr(self, '_stream')
                    consecutive_errors = 0
                    time.sleep(1)
                else:
                    time.sleep(0.1)
                continue
            else:
                consecutive_errors = 0  # Reset error counter on success
            
            # Resize
            frame = imutils.resize(frame, width=self.frame_width)
            
            # Detect (only if enabled)
            if self.enable_face_detection:
                self.current_faces = self.detect_faces(frame)
            else:
                self.current_faces = []
            
            if self.enable_object_detection:
                self.current_objects = self.detect_objects(frame)
            else:
                self.current_objects = []
            
            # Draw
            frame = self.draw_detections(frame, self.current_faces, self.current_objects)
            
            # Calculate FPS
            fps_counter += 1
            elapsed = time.time() - fps_start_time
            if elapsed > 1.0:
                self.fps = fps_counter / elapsed
                fps_counter = 0
                fps_start_time = time.time()
            
            # Add info overlay
            cv2.putText(frame, f"FPS: {self.fps:.1f}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.putText(frame, f"Faces: {len(self.current_faces)}, Objects: {len(self.current_objects)}",
                       (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            self.frame_count += 1
            
            # Convert to base64 for web
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            
            # Send via WebSocket
            if self.socketio:
                self.socketio.emit('frame', {
                    'image': f'data:image/jpeg;base64,{img_base64}',
                    'fps': round(self.fps, 1),
                    'faces': len(self.current_faces),
                    'objects': len(self.current_objects),
                    'frame_count': self.frame_count
                })
            
            # Calculate adaptive delay to achieve target FPS
            frame_process_time = time.time() - frame_start_time
            target_frame_time = 1.0 / self.target_fps
            sleep_time = max(0.001, target_frame_time - frame_process_time)
            
            # Extra delay for capture mode to prevent overwhelming ESP32CAM
            if '/capture' in self.stream_url.lower():
                sleep_time += 0.05  # Add 50ms delay for ESP32CAM capture endpoint
            
            time.sleep(sleep_time)
    
    def start(self):
        """Start processing."""
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._processing_loop)
            self.thread.daemon = True
            self.thread.start()
            return True
        return False
    
    def stop(self):
        """Stop processing."""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
        if hasattr(self, '_stream'):
            self._stream.close()
            delattr(self, '_stream')
        return True
    
    def update_params(self, **kwargs):
        """Update processing parameters."""
        if 'confidence' in kwargs:
            self.confidence_threshold = float(kwargs['confidence'])
        if 'scale_factor' in kwargs:
            self.face_scale_factor = float(kwargs['scale_factor'])
        if 'min_neighbors' in kwargs:
            self.face_min_neighbors = int(kwargs['min_neighbors'])
        if 'frame_width' in kwargs:
            self.frame_width = int(kwargs['frame_width'])
        if 'target_fps' in kwargs:
            self.target_fps = max(1, min(60, int(kwargs['target_fps'])))
        if 'enable_face' in kwargs:
            # Handle both boolean and string values from JSON
            val = kwargs['enable_face']
            if isinstance(val, str):
                self.enable_face_detection = val.lower() == 'true'
            else:
                self.enable_face_detection = bool(val)
        if 'enable_object' in kwargs:
            # Handle both boolean and string values from JSON
            val = kwargs['enable_object']
            if isinstance(val, str):
                self.enable_object_detection = val.lower() == 'true'
            else:
                self.enable_object_detection = bool(val)
        return True
