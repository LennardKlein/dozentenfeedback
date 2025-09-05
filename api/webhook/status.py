"""
Status check endpoint for queued tasks.
"""

import json
import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from upstash_redis import Redis

redis = Redis(
    url=os.environ.get("UPSTASH_REDIS_REST_URL"),
    token=os.environ.get("UPSTASH_REDIS_REST_TOKEN")
)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Get task status."""
        try:
            # Parse query parameters
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            task_id = query_params.get('task_id', [''])[0]
            
            if not task_id:
                self.send_error(400, "Missing required parameter: task_id")
                return
            
            # Get task from Redis
            task_data = redis.get(f"task:{task_id}")
            
            if not task_data:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {'error': 'Task not found', 'task_id': task_id}
                self.wfile.write(json.dumps(response).encode())
                return
            
            task = json.loads(task_data)
            
            # Check for result if completed
            if task.get('status') == 'completed':
                result = redis.get(f"result:{task_id}")
                if result:
                    task['result'] = json.loads(result)
            
            # Remove sensitive data
            task.pop('callback_url', None)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(task).encode())
            
        except Exception as e:
            print(f"Error getting task status: {e}")
            self.send_error(500, f"Internal server error: {str(e)}")