"""
Check status and retrieve results when ready
"""

import json
import os
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Check status of a task"""
        # Parse query parameters
        query = self.path.split('?')[1] if '?' in self.path else ''
        params = dict(p.split('=') for p in query.split('&') if '=' in p)
        task_id = params.get('task_id')
        
        if not task_id:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'No task_id provided'}).encode())
            return
        
        # Check for result
        result_file = f"/tmp/result_{task_id}.json"
        if os.path.exists(result_file):
            with open(result_file, 'r') as f:
                result = json.load(f)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        else:
            # Still processing
            metadata_file = f"/tmp/metadata_{task_id}.json"
            if os.path.exists(metadata_file):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {
                    'success': True,
                    'task_id': task_id,
                    'status': 'processing',
                    'message': 'Still processing, check back in a few minutes'
                }
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Task not found'}).encode())
    
    def do_POST(self):
        """Alternative POST method for status check"""
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data.decode('utf-8'))
        
        task_id = data.get('task_id')
        
        if not task_id:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'No task_id provided'}).encode())
            return
        
        # Check for result
        result_file = f"/tmp/result_{task_id}.json"
        if os.path.exists(result_file):
            with open(result_file, 'r') as f:
                result = json.load(f)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        else:
            # Still processing
            metadata_file = f"/tmp/metadata_{task_id}.json"
            if os.path.exists(metadata_file):
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {
                    'success': True,
                    'task_id': task_id,
                    'status': 'processing',
                    'message': 'Still processing, check back in a few minutes'
                }
                self.wfile.write(json.dumps(response).encode())
            else:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Task not found'}).encode())