"""
Submit video to AssemblyAI and return immediately
AssemblyAI will call us back when done
"""

import json
import os
import sys
import hashlib
from http.server import BaseHTTPRequestHandler
import assemblyai as aai
from datetime import datetime

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Submit video to AssemblyAI with webhook callback"""
        try:
            # Parse request
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Extract video URL
            video_url = (
                data.get('video_url') or 
                data.get('Video Files Download URL') or
                data.get('url')
            )
            
            if not video_url:
                self.send_error(400, "No video URL found")
                return
            
            # Extract metadata
            metadata = {
                'topic': data.get('Topic') or data.get('topic', 'Unknown'),
                'host_email': data.get('Host Email') or data.get('host_email', 'Unknown'),
                'duration': data.get('Duration') or data.get('duration', 'Unknown'),
                'meeting_id': data.get('Meeting ID') or data.get('meeting_id', 'Unknown')
            }
            
            # Create task ID
            task_id = hashlib.md5(video_url.encode()).hexdigest()[:12]
            
            # Configure AssemblyAI
            aai.settings.api_key = os.environ.get('ASSEMBLYAI_API_KEY')
            
            # Get our callback URL
            base_url = f"https://{os.environ.get('VERCEL_URL', 'dozentenfeedback.vercel.app')}"
            webhook_url = f"{base_url}/api/webhook/assemblyai-callback"
            
            # Submit to AssemblyAI with webhook
            config = aai.TranscriptionConfig(
                speaker_labels=True,
                punctuate=True,
                disfluencies=False,
                webhook_url=webhook_url,
                webhook_auth_header_name="X-Task-ID",
                webhook_auth_header_value=task_id
            )
            
            # Start transcription
            transcriber = aai.Transcriber()
            transcript = transcriber.submit(video_url, config=config)
            
            # Store metadata for later (in production, use a database)
            # For now, save to /tmp
            import tempfile
            metadata_file = f"/tmp/metadata_{task_id}.json"
            with open(metadata_file, 'w') as f:
                json.dump({
                    'metadata': metadata,
                    'transcript_id': transcript.id,
                    'task_id': task_id,
                    'submitted_at': datetime.now().isoformat()
                }, f)
            
            # Return immediately
            response = {
                'success': True,
                'task_id': task_id,
                'transcript_id': transcript.id,
                'status': 'submitted',
                'message': 'Video submitted for processing. You will receive results via webhook.',
                'estimated_time': self.estimate_time(metadata.get('duration', '60')),
                'webhook_will_call': data.get('callback_url', 'Not provided - results will be stored'),
                'check_status_url': f"{base_url}/api/webhook/check-status?task_id={task_id}"
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"Error: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(error_response).encode())
    
    def estimate_time(self, duration_str):
        """Estimate processing time based on duration"""
        try:
            # Parse duration (format: "71" for minutes)
            minutes = int(duration_str)
            # AssemblyAI typically takes 25-30% of audio duration
            processing_minutes = int(minutes * 0.3)
            # Add time for OpenAI analysis
            total_minutes = processing_minutes + 2
            return f"{total_minutes} minutes"
        except:
            return "5-10 minutes"
    
    def do_GET(self):
        """Health check"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {'status': 'ready', 'service': 'DozentenFeedback-AssemblyAI-Submit'}
        self.wfile.write(json.dumps(response).encode())