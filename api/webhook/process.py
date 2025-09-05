"""
Webhook endpoint for Zapier integration.
Receives video URLs and initiates async processing.
"""

import json
import os
import uuid
from http.server import BaseHTTPRequestHandler
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

import httpx
from upstash_redis import Redis

redis = Redis(
    url=os.environ.get("UPSTASH_REDIS_REST_URL"),
    token=os.environ.get("UPSTASH_REDIS_REST_TOKEN")
)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle POST request from Zapier."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            content_type = self.headers.get('Content-Type', '')
            
            if 'application/json' in content_type:
                data = json.loads(post_data.decode('utf-8'))
            elif 'application/x-www-form-urlencoded' in content_type:
                parsed_data = parse_qs(post_data.decode('utf-8'))
                data = {k: v[0] if len(v) == 1 else v for k, v in parsed_data.items()}
            else:
                data = json.loads(post_data.decode('utf-8'))
            
            # Extract video URL from Zoom data structure
            # Priority: direct video_url > video_files_download_url_1 > fallback to audio
            video_url = (
                data.get('video_url') or 
                data.get('video_files_download_url_1') or
                data.get('Video Files Download URL') or
                data.get('audio_files_download_url_1') or
                data.get('Audio Files Download URL') or
                data.get('url')
            )
            
            callback_url = data.get('callback_url') or data.get('webhook_url')
            
            if not video_url:
                self.send_error(400, "Missing required field: video_url or audio_url")
                return
            
            # Generate task ID
            task_id = str(uuid.uuid4())
            
            # Extract Zoom metadata if available
            metadata = data.get('metadata', {})
            
            # Also check for top-level Zoom fields
            zoom_fields = {
                'topic': data.get('Topic') or data.get('topic'),
                'host_email': data.get('Host Email') or data.get('host_email'),
                'meeting_id': data.get('Meeting ID') or data.get('meeting_id'),
                'duration': data.get('Duration') or data.get('duration'),
                'start_time': data.get('Start Time') or data.get('start_time'),
                'share_url': data.get('Share URL') or data.get('share_url')
            }
            
            # Merge zoom fields into metadata
            for key, value in zoom_fields.items():
                if value and key not in metadata:
                    metadata[key] = value
            
            # Store task in Redis
            task_data = {
                'id': task_id,
                'video_url': video_url,
                'callback_url': callback_url,
                'status': 'queued',
                'created_at': str(int(os.times().elapsed * 1000)),
                'metadata': metadata
            }
            
            redis.set(f"task:{task_id}", json.dumps(task_data), ex=86400)  # 24h expiry
            
            # Queue the task for async processing
            redis.lpush("video_processing_queue", task_id)
            
            # Trigger async processing (Vercel Edge Function)
            base_url = f"https://{self.headers.get('Host', 'localhost')}"
            trigger_url = f"{base_url}/api/tasks/process-video"
            
            try:
                # Fire and forget - don't wait for response
                with httpx.Client(timeout=5.0) as client:
                    client.post(
                        trigger_url,
                        json={'task_id': task_id},
                        headers={'Authorization': f"Bearer {os.environ.get('WEBHOOK_SECRET')}"}
                    )
            except Exception as e:
                # Log but don't fail - task is queued
                print(f"Failed to trigger async processing: {e}")
            
            # Return immediate response to Zapier
            response = {
                'success': True,
                'task_id': task_id,
                'status': 'queued',
                'status_url': f"{base_url}/api/webhook/status?task_id={task_id}",
                'message': 'Video processing queued successfully'
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON payload")
        except Exception as e:
            print(f"Error processing webhook: {e}")
            self.send_error(500, f"Internal server error: {str(e)}")
    
    def do_GET(self):
        """Health check endpoint."""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {'status': 'healthy', 'service': 'video-transcription-webhook'}
        self.wfile.write(json.dumps(response).encode())