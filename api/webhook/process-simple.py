"""
Production Vercel webhook handler that generates PDF reports
Processes videos directly and returns PDF as base64 for Zapier to handle storage
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from app.transcription_url import transcribe_from_url
from app.chunker import TranscriptionChunker
from app.analyzer import LectureAnalyzer
from app.aggregator import ScoreAggregator
from app.formatter import MarkdownFormatter
from app.pdf_formatter import PDFReportGenerator

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Process video, generate PDF report, and save to Google Drive"""
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
                'host_email': data.get('Host Email') or data.get('host_email', os.environ.get('USER_EMAIL', 'Unknown')),
                'duration': data.get('Duration') or data.get('duration', 'Unknown'),
                'meeting_id': data.get('Meeting ID') or data.get('meeting_id', 'Unknown')
            }
            
            # Process video
            print(f"Processing video: {video_url[:100]}...")
            print(f"Metadata: {metadata}")
            
            # Step 1: Transcribe
            print("Step 1: Transcribing with AssemblyAI...")
            vtt_content = transcribe_from_url(video_url, metadata=metadata)
            
            # Step 2: Chunk
            print("Step 2: Chunking transcription...")
            chunker = TranscriptionChunker()
            blocks = chunker.chunk_from_vtt_content(vtt_content)
            print(f"Created {len(blocks)} blocks")
            
            # Step 3: Analyze
            print("Step 3: Analyzing blocks with OpenAI...")
            analyzer = LectureAnalyzer()
            block_analyses = []
            for i, block in enumerate(blocks):
                print(f"Analyzing block {i+1}/{len(blocks)}...")
                analysis = analyzer.analyze_block(block)
                block_analyses.append(analysis)
            
            # Step 4: Aggregate
            print("Step 4: Aggregating results...")
            aggregator = ScoreAggregator()
            complete_report = aggregator.create_complete_report(block_analyses)
            
            # Step 5: Format as markdown (for reference)
            formatter = MarkdownFormatter()
            markdown_report = formatter.format_complete_report(complete_report)
            kurzfassung = formatter.format_kurzfassung(complete_report)
            
            # Step 6: Generate PDF
            print("Step 6: Generating PDF report...")
            pdf_generator = PDFReportGenerator()
            
            # Prepare report data for PDF
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
            
            # Add score to metadata
            metadata['score'] = complete_report.overall_score
            
            pdf_bytes = pdf_generator.generate_report_pdf(report_data, metadata)
            
            # Step 7: Prepare PDF for Zapier
            import base64
            
            # Generate filename for Zapier to use
            date = metadata.get('date', '')
            if not date:
                from datetime import datetime
                date = datetime.now().strftime('%Y%m%d_%H%M')
            
            topic = metadata.get('topic', 'Unknown').replace('/', '-').replace(' ', '_')[:50]
            host = metadata.get('host_email', 'unknown').split('@')[0]
            
            suggested_filename = f"DozentenFeedback_{date}_{host}_{topic}.pdf"
            
            # Clean filename
            invalid_chars = '<>:"/\\|?*'
            for char in invalid_chars:
                suggested_filename = suggested_filename.replace(char, '_')
            
            # Convert PDF to base64 for Zapier
            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
            
            print(f"Step 7: PDF ready for Zapier (size: {len(pdf_bytes)} bytes)")
            
            # Prepare response for Zapier
            result = {
                'success': True,
                'overall_score': complete_report.overall_score,
                'blocks_analyzed': len(blocks),
                'summary': kurzfassung,
                'metadata': metadata,
                'processing_complete': True,
                'message': f"Analysis complete. Score: {complete_report.overall_score:.1f}/5.0",
                # PDF data for Zapier to save
                'pdf_filename': suggested_filename,
                'pdf_base64': pdf_base64,
                'pdf_size_bytes': len(pdf_bytes)
            }
            
            # Return results to Zapier
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            
            print(f"Processing complete. Overall score: {complete_report.overall_score:.1f}/5.0")
            
            # Optional: Send to callback URL if provided
            callback_url = data.get('callback_url')
            if callback_url:
                import httpx
                try:
                    with httpx.Client(timeout=30) as client:
                        callback_response = client.post(callback_url, json=result)
                        print(f"Callback sent to {callback_url}: {callback_response.status_code}")
                except Exception as e:
                    print(f"Could not send callback: {e}")
            
        except Exception as e:
            print(f"Error processing video: {e}")
            import traceback
            traceback.print_exc()
            
            error_result = {
                'success': False,
                'error': str(e),
                'message': 'Processing failed'
            }
            
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(error_result).encode())
    
    def do_GET(self):
        """Health check endpoint"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {
            'status': 'ready',
            'service': 'DozentenFeedback',
            'version': '1.0.0',
            'features': {
                'transcription': 'AssemblyAI',
                'analysis': 'OpenAI GPT-4',
                'storage': 'Google Drive',
                'format': 'PDF'
            }
        }
        self.wfile.write(json.dumps(response).encode())