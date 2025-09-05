"""
Split processing webhook - handles both start and retrieve
Uses Vercel KV or temporary storage for state
"""

import json
import os
import sys
import hashlib
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Simple file-based storage for Vercel (in /tmp which persists during function lifetime)
STORAGE_PATH = "/tmp/tasks"

def ensure_storage():
    """Ensure storage directory exists"""
    os.makedirs(STORAGE_PATH, exist_ok=True)

def save_task(task_id, data):
    """Save task data to file"""
    ensure_storage()
    with open(f"{STORAGE_PATH}/{task_id}.json", "w") as f:
        json.dump(data, f)

def load_task(task_id):
    """Load task data from file"""
    ensure_storage()
    task_file = f"{STORAGE_PATH}/{task_id}.json"
    if os.path.exists(task_file):
        with open(task_file, "r") as f:
            return json.load(f)
    return None

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle both start and retrieve operations"""
        try:
            # Parse request
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Check if this is a retrieve request
            if data.get('action') == 'retrieve' or data.get('task_id'):
                # This is a retrieve request
                task_id = data.get('task_id')
                if not task_id:
                    self.send_error(400, "No task_id provided")
                    return
                
                # Load task result
                task_data = load_task(task_id)
                
                if not task_data:
                    # Task doesn't exist, might need to process
                    if data.get('video_url'):
                        # Process now
                        result = self.process_video_now(data)
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(result).encode())
                    else:
                        self.send_response(404)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'error': 'Task not found'}).encode())
                    return
                
                # Return the stored result
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(task_data).encode())
                return
            
            # This is a start request
            video_url = (
                data.get('video_url') or 
                data.get('Video Files Download URL') or
                data.get('url')
            )
            
            if not video_url:
                self.send_error(400, "No video URL found")
                return
            
            # Create task ID from video URL
            task_id = hashlib.md5(video_url.encode()).hexdigest()[:12]
            
            # Check if already processed
            existing = load_task(task_id)
            if existing and existing.get('status') == 'completed':
                # Already done, return it
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(existing).encode())
                return
            
            # Try to process immediately (we have up to 5 minutes on Vercel)
            # But return within 25 seconds for Zapier
            start_time = time.time()
            timeout = 25  # seconds
            
            # Start processing
            result = self.process_with_timeout(data, timeout)
            
            if result:
                # Processing completed within timeout
                save_task(task_id, result)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
            else:
                # Processing taking too long, return task_id for later retrieval
                response = {
                    'success': True,
                    'task_id': task_id,
                    'status': 'processing',
                    'message': 'Processing in progress, check back in 2-3 minutes',
                    'retry_after': 120,  # seconds
                    'retrieve_with': {
                        'action': 'retrieve',
                        'task_id': task_id,
                        'video_url': video_url  # Include for fallback processing
                    }
                }
                self.send_response(202)  # Accepted
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(error_response).encode())
    
    def process_with_timeout(self, data, timeout):
        """Try to process within timeout, return None if taking too long"""
        import threading
        result = {'status': 'timeout'}
        
        def process():
            try:
                result['data'] = self.process_video_now(data)
                result['status'] = 'completed'
            except Exception as e:
                result['status'] = 'error'
                result['error'] = str(e)
        
        thread = threading.Thread(target=process)
        thread.daemon = True
        thread.start()
        thread.join(timeout)
        
        if result['status'] == 'completed':
            return result['data']
        return None
    
    def process_video_now(self, data):
        """Process video immediately"""
        from app.transcription_url import transcribe_from_url
        from app.chunker import TranscriptionChunker
        from app.analyzer import LectureAnalyzer
        from app.aggregator import ScoreAggregator
        from app.formatter import MarkdownFormatter
        from app.pdf_formatter import PDFReportGenerator
        import base64
        
        video_url = (
            data.get('video_url') or 
            data.get('Video Files Download URL') or
            data.get('url')
        )
        
        metadata = {
            'topic': data.get('Topic') or data.get('topic', 'Unknown'),
            'host_email': data.get('Host Email') or data.get('host_email', 'Unknown'),
            'duration': data.get('Duration') or data.get('duration', 'Unknown'),
            'meeting_id': data.get('Meeting ID') or data.get('meeting_id', 'Unknown')
        }
        
        print(f"Processing video: {video_url[:100]}...")
        
        # Process video
        vtt_content = transcribe_from_url(video_url, metadata=metadata)
        
        chunker = TranscriptionChunker()
        blocks = chunker.chunk_from_vtt_content(vtt_content)
        
        analyzer = LectureAnalyzer()
        block_analyses = []
        for block in blocks:
            analysis = analyzer.analyze_block(block)
            block_analyses.append(analysis)
        
        aggregator = ScoreAggregator()
        complete_report = aggregator.create_complete_report(block_analyses)
        
        formatter = MarkdownFormatter()
        kurzfassung = formatter.format_kurzfassung(complete_report)
        
        # Generate PDF
        pdf_generator = PDFReportGenerator()
        report_data = {
            'overall_score': complete_report.overall_score,
            'total_blocks': len(blocks),
            'criteria_scores': {
                criterion.name: score 
                for criterion, score in complete_report.criteria_scores.items()
            },
            'summary': kurzfassung,
            'strengths': complete_report.overall_strengths[:5] if complete_report.overall_strengths else [],
            'improvements': complete_report.overall_improvements[:5] if complete_report.overall_improvements else [],
            'recommendations': complete_report.recommendations[:5] if complete_report.recommendations else []
        }
        
        metadata['score'] = complete_report.overall_score
        pdf_bytes = pdf_generator.generate_report_pdf(report_data, metadata)
        
        # Generate filename
        date = datetime.now().strftime('%Y%m%d_%H%M')
        topic = metadata.get('topic', 'Unknown').replace('/', '-').replace(' ', '_')[:50]
        host = metadata.get('host_email', 'unknown').split('@')[0]
        suggested_filename = f"DozentenFeedback_{date}_{host}_{topic}.pdf"
        
        # Convert to base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        return {
            'success': True,
            'status': 'completed',
            'overall_score': complete_report.overall_score,
            'blocks_analyzed': len(blocks),
            'summary': kurzfassung,
            'metadata': metadata,
            'pdf_filename': suggested_filename,
            'pdf_base64': pdf_base64,
            'pdf_size_bytes': len(pdf_bytes),
            'message': f"Analysis complete. Score: {complete_report.overall_score:.1f}/5.0"
        }
    
    def do_GET(self):
        """Health check"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {'status': 'ready', 'service': 'DozentenFeedback-Split'}
        self.wfile.write(json.dumps(response).encode())