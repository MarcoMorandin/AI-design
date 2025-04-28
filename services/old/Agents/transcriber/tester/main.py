from flask import Flask, jsonify, send_from_directory, request, Response
from flask_cors import CORS
import os
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)
# Enable CORS for all routes
CORS(app, resources={r"/*": {"origins": "*"}})

# Configuration
VIDEO_FOLDER = 'videos'  # Folder where your videos are stored
PORT = 5005
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

# Ensure the video folder exists
os.makedirs(VIDEO_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/videos', methods=['GET'])
def list_videos():
    """API endpoint to list all available videos"""
    videos = []
    for filename in os.listdir(VIDEO_FOLDER):
        if allowed_file(filename):
            file_path = os.path.join(VIDEO_FOLDER, filename)
            file_size = os.path.getsize(file_path)
            videos.append({
                'filename': filename,
                'size_bytes': file_size,
                'url': f'/api/videos/{filename}'
            })
    return jsonify({'videos': videos})

@app.route('/api/videos/<filename>', methods=['GET'])
def get_video(filename):
    """API endpoint to stream a specific video"""
    filename = secure_filename(filename)
    if os.path.exists(os.path.join(VIDEO_FOLDER, filename)):
        return send_from_directory(VIDEO_FOLDER, filename)
    else:
        return jsonify({'error': 'Video not found'}), 404

@app.route('/api/videos', methods=['POST'])
def upload_video():
    """API endpoint to upload a new video"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(VIDEO_FOLDER, filename)
        file.save(file_path)
        return jsonify({
            'message': 'Upload successful',
            'filename': filename,
            'url': f'/api/videos/{filename}'
        }), 201
    else:
        return jsonify({'error': 'File type not allowed'}), 400

@app.route('/api/videos/<filename>', methods=['DELETE'])
def delete_video(filename):
    """API endpoint to delete a video"""
    filename = secure_filename(filename)
    file_path = os.path.join(VIDEO_FOLDER, filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({'message': f'Video {filename} deleted successfully'}), 200
    else:
        return jsonify({'error': 'Video not found'}), 404

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({'status': 'online', 'service': 'video-api'})

@app.route('/')
def index():
    """Simple documentation page"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Video API Documentation</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
            h1 { color: #333; }
            h2 { color: #555; margin-top: 30px; }
            code { background: #f4f4f4; padding: 2px 5px; border-radius: 3px; }
            pre { background: #f8f8f8; padding: 15px; border-radius: 5px; overflow-x: auto; }
            .endpoint { margin-bottom: 30px; border-left: 4px solid #ddd; padding-left: 15px; }
        </style>
    </head>
    <body>
        <h1>Video API Documentation</h1>
        <p><strong>CORS is enabled</strong> - This API can be accessed from different origins/domains.</p>
        
        <div class="endpoint">
            <h2>List all videos</h2>
            <p><code>GET /api/videos</code></p>
            <p>Returns a list of all available videos.</p>
        </div>
        
        <div class="endpoint">
            <h2>Get a specific video</h2>
            <p><code>GET /api/videos/{filename}</code></p>
            <p>Streams the requested video file.</p>
        </div>
        
        <div class="endpoint">
            <h2>Upload a video</h2>
            <p><code>POST /api/videos</code></p>
            <p>Upload a new video file.</p>
            <pre>Content-Type: multipart/form-data
Form parameter: file</pre>
        </div>
        
        <div class="endpoint">
            <h2>Delete a video</h2>
            <p><code>DELETE /api/videos/{filename}</code></p>
            <p>Delete an existing video file.</p>
        </div>
        
        <div class="endpoint">
            <h2>Health Check</h2>
            <p><code>GET /api/health</code></p>
            <p>Check if the service is running.</p>
        </div>
    </body>
    </html>
    '''

if __name__ == '__main__':
    print(f"Video API server started at http://localhost:{PORT}")
    print(f"Videos are stored in the '{VIDEO_FOLDER}' folder")
    print("Available API endpoints:")
    print(f"  - GET    http://localhost:{PORT}/api/videos")
    print(f"  - GET    http://localhost:{PORT}/api/videos/filename.mp4")
    print(f"  - POST   http://localhost:{PORT}/api/videos")
    print(f"  - DELETE http://localhost:{PORT}/api/videos/filename.mp4")
    print(f"  - GET    http://localhost:{PORT}/api/health")
    print("CORS is enabled - API can be accessed from any origin")
    print("Press Ctrl+C to stop the server.")
    app.run(host='0.0.0.0', port=PORT, debug=True)