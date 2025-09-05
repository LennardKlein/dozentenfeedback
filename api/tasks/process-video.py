"""
Async video processing task handler.
This runs as a Vercel Edge Function with extended timeout.
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict
import traceback

import httpx
from upstash_redis import Redis

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from app.transcription_url import transcribe_from_url
from app.chunker import TranscriptionChunker
from app.analyzer import LectureAnalyzer
from app.aggregator import ScoreAggregator
from app.formatter import MarkdownFormatter

redis = Redis(
    url=os.environ.get("UPSTASH_REDIS_REST_URL"),
    token=os.environ.get("UPSTASH_REDIS_REST_TOKEN")
)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Process video transcription task."""
        try:
            # Verify internal auth
            auth_header = self.headers.get('Authorization', '')
            expected_token = f"Bearer {os.environ.get('WEBHOOK_SECRET')}"
            
            if auth_header != expected_token:
                self.send_error(401, "Unauthorized")
                return
            
            # Parse request
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            task_id = data.get('task_id')
            if not task_id:
                self.send_error(400, "Missing task_id")
                return
            
            # Get task from Redis
            task_data = redis.get(f"task:{task_id}")
            if not task_data:
                self.send_error(404, "Task not found")
                return
            
            task = json.loads(task_data)
            
            # Update status to processing
            task['status'] = 'processing'
            redis.set(f"task:{task_id}", json.dumps(task), ex=86400)
            
            try:
                # Process video with metadata
                result = self._process_video(task['video_url'], task.get('metadata', {}))
                
                # Store result
                redis.set(f"result:{task_id}", json.dumps(result), ex=86400)
                
                # Update task status
                task['status'] = 'completed'
                task['completed_at'] = str(int(os.times().elapsed * 1000))
                redis.set(f"task:{task_id}", json.dumps(task), ex=86400)
                
                # Send callback to Zapier if URL provided
                if task.get('callback_url'):
                    self._send_callback(task['callback_url'], task_id, result)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                response = {'success': True, 'task_id': task_id}
                self.wfile.write(json.dumps(response).encode())
                
            except Exception as e:
                # Update task with error
                error_msg = str(e)
                task['status'] = 'failed'
                task['error'] = error_msg
                task['failed_at'] = str(int(os.times().elapsed * 1000))
                redis.set(f"task:{task_id}", json.dumps(task), ex=86400)
                
                # Send error callback
                if task.get('callback_url'):
                    self._send_error_callback(task['callback_url'], task_id, error_msg)
                
                raise
                
        except Exception as e:
            print(f"Error processing video: {e}")
            print(traceback.format_exc())
            self.send_error(500, f"Processing error: {str(e)}")
    
    def _process_video(self, video_url: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process video and return analysis results."""
        
        # Step 1: Transcribe video
        print(f"Transcribing video from URL: {video_url}")
        vtt_content = transcribe_from_url(video_url, metadata=metadata)
        
        # Step 2: Chunk transcription
        chunker = TranscriptionChunker()
        blocks = chunker.chunk_from_vtt_content(vtt_content)
        
        if not blocks:
            raise ValueError("No analyzable blocks found in transcription")
        
        # Step 3: Analyze blocks
        analyzer = LectureAnalyzer()
        block_analyses = []
        
        for block in blocks:
            analysis = analyzer.analyze_block(block)
            block_analyses.append(analysis)
        
        # Step 4: Aggregate results
        aggregator = ScoreAggregator()
        complete_report = aggregator.create_complete_report(block_analyses)
        
        # Step 5: Format results
        formatter = MarkdownFormatter()
        
        return {
            'overall_score': complete_report.overall_score,
            'timestamp': complete_report.timestamp.isoformat(),
            'markdown_report': formatter.format_complete_report(complete_report),
            'kurzfassung': formatter.format_kurzfassung(complete_report),
            'json_report': json.loads(formatter.format_json_report(complete_report)),
            'transcription': vtt_content,
            'blocks_analyzed': len(blocks)
        }
    
    def _send_callback(self, callback_url: str, task_id: str, result: Dict[str, Any]):
        """Send success callback to Zapier."""
        try:
            with httpx.Client(timeout=30.0) as client:
                payload = {
                    'task_id': task_id,
                    'status': 'completed',
                    'result': result
                }
                response = client.post(callback_url, json=payload)
                print(f"Callback sent to {callback_url}: {response.status_code}")
        except Exception as e:
            print(f"Failed to send callback: {e}")
    
    def _send_error_callback(self, callback_url: str, task_id: str, error: str):
        """Send error callback to Zapier."""
        try:
            with httpx.Client(timeout=30.0) as client:
                payload = {
                    'task_id': task_id,
                    'status': 'failed',
                    'error': error
                }
                response = client.post(callback_url, json=payload)
                print(f"Error callback sent to {callback_url}: {response.status_code}")
        except Exception as e:
            print(f"Failed to send error callback: {e}")