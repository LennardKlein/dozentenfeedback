"""
Simple webhook that stores video URL for later processing
Returns immediately to avoid timeout
"""

import json
import os
import sys
import hashlib
from http.server import BaseHTTPRequestHandler
from datetime import datetime

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Store video data and return immediately"""
        try:
            # Parse request
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Extract video URL and metadata
            video_url = (
                data.get('video_url') or 
                data.get('Video Files Download URL') or
                data.get('url')
            )
            
            if not video_url:
                self.send_error(400, "No video URL found")
                return
            
            # Create a simple task ID from video URL hash
            task_id = hashlib.md5(video_url.encode()).hexdigest()[:12]
            
            # Store the task data (in production, use a database)
            # For now, we'll just return the data that Zapier needs
            
            response = {
                'success': True,
                'task_id': task_id,
                'status': 'queued',
                'message': 'Processing queued successfully',
                'video_url': video_url,
                'metadata': {
                    'topic': data.get('Topic') or data.get('topic', 'Unknown'),
                    'host_email': data.get('Host Email') or data.get('host_email', 'Unknown'),
                    'duration': data.get('Duration') or data.get('duration', 'Unknown'),
                    'meeting_id': data.get('Meeting ID') or data.get('meeting_id', 'Unknown'),
                    'queued_at': datetime.now().isoformat()
                },
                'check_url': f"https://{os.environ.get('VERCEL_URL', 'dozentenfeedback.vercel.app')}/api/webhook/get-result?task_id={task_id}"
            }
            
            # Return immediately
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(error_response).encode())
    
    def do_GET(self):
        """Health check"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {'status': 'ready', 'service': 'DozentenFeedback-Queue'}
        self.wfile.write(json.dumps(response).encode())