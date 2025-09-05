"""
Async Vercel webhook handler - returns immediately and processes in background
"""

import json
import os
import sys
import uuid
import time
from http.server import BaseHTTPRequestHandler
from pathlib import Path
import threading

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# Simple in-memory storage (replace with database in production)
processing_tasks = {}

def process_video_async(task_id, data):
    """Process video in background thread"""
    try:
        from app.transcription_url import transcribe_from_url
        from app.chunker import TranscriptionChunker
        from app.analyzer import LectureAnalyzer
        from app.aggregator import ScoreAggregator
        from app.formatter import MarkdownFormatter
        from app.pdf_formatter import PDFReportGenerator
        import base64
        from datetime import datetime
        
        # Update status
        processing_tasks[task_id]['status'] = 'processing'
        processing_tasks[task_id]['started_at'] = time.time()
        
        # Extract video URL and metadata
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
        
        # Process video
        print(f"Task {task_id}: Processing video: {video_url[:100]}...")
        
        # Step 1: Transcribe
        vtt_content = transcribe_from_url(video_url, metadata=metadata)
        processing_tasks[task_id]['progress'] = 'Transcription complete'
        
        # Step 2: Chunk
        chunker = TranscriptionChunker()
        blocks = chunker.chunk_from_vtt_content(vtt_content)
        processing_tasks[task_id]['progress'] = f'Chunked into {len(blocks)} blocks'
        
        # Step 3: Analyze
        analyzer = LectureAnalyzer()
        block_analyses = []
        for i, block in enumerate(blocks):
            analysis = analyzer.analyze_block(block)
            block_analyses.append(analysis)
            processing_tasks[task_id]['progress'] = f'Analyzed {i+1}/{len(blocks)} blocks'
        
        # Step 4: Aggregate
        aggregator = ScoreAggregator()
        complete_report = aggregator.create_complete_report(block_analyses)
        
        # Step 5: Format
        formatter = MarkdownFormatter()
        kurzfassung = formatter.format_kurzfassung(complete_report)
        
        # Step 6: Generate PDF
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
        
        # Store results
        processing_tasks[task_id]['status'] = 'completed'
        processing_tasks[task_id]['completed_at'] = time.time()
        processing_tasks[task_id]['result'] = {
            'success': True,
            'overall_score': complete_report.overall_score,
            'blocks_analyzed': len(blocks),
            'summary': kurzfassung,
            'metadata': metadata,
            'pdf_filename': suggested_filename,
            'pdf_base64': pdf_base64,
            'pdf_size_bytes': len(pdf_bytes),
            'processing_time': time.time() - processing_tasks[task_id]['started_at']
        }
        
        print(f"Task {task_id}: Completed successfully")
        
    except Exception as e:
        print(f"Task {task_id}: Failed with error: {e}")
        processing_tasks[task_id]['status'] = 'failed'
        processing_tasks[task_id]['error'] = str(e)
        processing_tasks[task_id]['completed_at'] = time.time()

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Start async processing and return task ID immediately"""
        try:
            # Parse request
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Check for status endpoint
            if self.path == '/api/webhook/status':
                task_id = data.get('task_id')
                if not task_id or task_id not in processing_tasks:
                    self.send_response(404)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'Task not found'}).encode())
                    return
                
                task = processing_tasks[task_id]
                response = {
                    'task_id': task_id,
                    'status': task['status'],
                    'progress': task.get('progress', ''),
                    'created_at': task['created_at']
                }
                
                if task['status'] == 'completed':
                    response.update(task['result'])
                elif task['status'] == 'failed':
                    response['error'] = task.get('error', 'Unknown error')
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                return
            
            # Create new task
            task_id = str(uuid.uuid4())
            processing_tasks[task_id] = {
                'status': 'queued',
                'created_at': time.time(),
                'data': data
            }
            
            # Start processing in background
            thread = threading.Thread(
                target=process_video_async,
                args=(task_id, data),
                daemon=True
            )
            thread.start()
            
            # Return immediately with task ID
            response = {
                'success': True,
                'task_id': task_id,
                'status': 'processing',
                'message': 'Video processing started',
                'status_url': f'{self.headers.get("Host", "")}/api/webhook/status'
            }
            
            self.send_response(202)  # 202 Accepted
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
        """Health check or status check"""
        if self.path.startswith('/api/webhook/status/'):
            # Get task ID from path
            task_id = self.path.split('/')[-1]
            
            if task_id not in processing_tasks:
                self.send_response(404)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': 'Task not found'}).encode())
                return
            
            task = processing_tasks[task_id]
            response = {
                'task_id': task_id,
                'status': task['status'],
                'progress': task.get('progress', ''),
                'created_at': task['created_at']
            }
            
            if task['status'] == 'completed':
                response.update(task['result'])
            elif task['status'] == 'failed':
                response['error'] = task.get('error', 'Unknown error')
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        else:
            # Health check
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {
                'status': 'ready',
                'service': 'DozentenFeedback-Async',
                'active_tasks': len([t for t in processing_tasks.values() if t['status'] == 'processing'])
            }
            self.wfile.write(json.dumps(response).encode())