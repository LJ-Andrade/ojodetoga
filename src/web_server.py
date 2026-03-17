from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import threading
import time
from stream_processor import StreamProcessor

app = Flask(__name__)
app.config['SECRET_KEY'] = 'esp32cam-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Global processor instance
processor = None


@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print('Client connected')
    emit('status', {'message': 'Connected', 'running': processor.is_running if processor else False})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    print('Client disconnected')


@socketio.on('start')
def handle_start(data):
    """Start processing."""
    global processor
    
    url = data.get('url', 'http://192.168.1.63:8080/video')
    camera_mode = data.get('mode', 'auto')
    
    if processor is None or not processor.is_running:
        processor = StreamProcessor(url, socketio, camera_mode)
        processor.start()
        emit('status', {'message': 'Processing started', 'running': True, 'url': url, 'mode': camera_mode})
    else:
        emit('status', {'message': 'Already running', 'running': True})


@socketio.on('stop')
def handle_stop():
    """Stop processing."""
    global processor
    
    if processor:
        processor.stop()
        emit('status', {'message': 'Processing stopped', 'running': False})
    else:
        emit('status', {'message': 'Not running', 'running': False})


@socketio.on('update_params')
def handle_update_params(data):
    """Update processing parameters."""
    global processor
    
    if processor:
        processor.update_params(**data)
        emit('params_updated', {'message': 'Parameters updated', 'params': data})
    else:
        emit('error', {'message': 'Processor not running'})


@socketio.on('get_status')
def handle_get_status():
    """Get current status."""
    global processor
    
    if processor:
        emit('status', {
            'running': processor.is_running,
            'fps': round(processor.fps, 1),
            'faces': len(processor.current_faces),
            'objects': len(processor.current_objects),
            'frame_count': processor.frame_count
        })
    else:
        emit('status', {'running': False})


if __name__ == '__main__':
    print("Starting ESP32CAM Web Interface")
    print("Open http://localhost:8080 in your browser")
    print("Or http://<your-ip>:8080 from other devices")
    socketio.run(app, host='0.0.0.0', port=8080, debug=False, allow_unsafe_werkzeug=True)
