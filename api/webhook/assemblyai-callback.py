"""
Callback endpoint for AssemblyAI
Receives transcription when complete and processes it
"""

import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Handle AssemblyAI webhook callback"""
        try:
            # Parse request
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Get task ID from header
            task_id = self.headers.get('X-Task-ID')
            
            print(f"Received callback for task {task_id}")
            print(f"Transcription status: {data.get('status')}")
            
            if data.get('status') != 'completed':
                # Transcription failed
                self.save_error(task_id, data.get('error', 'Transcription failed'))
                self.send_response(200)
                self.end_headers()
                return
            
            # Load metadata
            metadata_file = f"/tmp/metadata_{task_id}.json"
            if os.path.exists(metadata_file):
                with open(metadata_file, 'r') as f:
                    task_data = json.load(f)
                    metadata = task_data.get('metadata', {})
            else:
                metadata = {}
            
            # Get transcription text with timestamps
            vtt_content = self.convert_to_vtt(data)
            
            # Now process with OpenAI
            from app.chunker import TranscriptionChunker
            from app.analyzer import LectureAnalyzer
            from app.aggregator import ScoreAggregator
            from app.formatter import MarkdownFormatter
            from app.pdf_formatter import PDFReportGenerator
            import base64
            from datetime import datetime
            
            print(f"Processing transcription for task {task_id}")
            
            # Chunk
            chunker = TranscriptionChunker()
            blocks = chunker.chunk_from_vtt_content(vtt_content)
            
            # Analyze
            analyzer = LectureAnalyzer()
            block_analyses = []
            for block in blocks:
                analysis = analyzer.analyze_block(block)
                block_analyses.append(analysis)
            
            # Aggregate
            aggregator = ScoreAggregator()
            complete_report = aggregator.create_complete_report(block_analyses)
            
            # Format
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
            
            # Save results
            result = {
                'success': True,
                'task_id': task_id,
                'status': 'completed',
                'overall_score': complete_report.overall_score,
                'blocks_analyzed': len(blocks),
                'summary': kurzfassung,
                'metadata': metadata,
                'pdf_filename': suggested_filename,
                'pdf_base64': pdf_base64,
                'pdf_size_bytes': len(pdf_bytes)
            }
            
            # Save to file for retrieval
            result_file = f"/tmp/result_{task_id}.json"
            with open(result_file, 'w') as f:
                json.dump(result, f)
            
            print(f"Task {task_id} completed successfully. Score: {complete_report.overall_score:.1f}/5.0")
            
            # Return success to AssemblyAI
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'success': True}).encode())
            
        except Exception as e:
            print(f"Error processing callback: {e}")
            import traceback
            traceback.print_exc()
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = {'success': False, 'error': str(e)}
            self.wfile.write(json.dumps(error_response).encode())
    
    def convert_to_vtt(self, assemblyai_data):
        """Convert AssemblyAI response to VTT format"""
        vtt_lines = ["WEBVTT\n\n"]
        
        # Get utterances if available (for speaker labels)
        utterances = assemblyai_data.get('utterances', [])
        if utterances:
            for utterance in utterances:
                start_time = self.ms_to_vtt_timestamp(utterance['start'])
                end_time = self.ms_to_vtt_timestamp(utterance['end'])
                speaker = f"Speaker {utterance.get('speaker', 'Unknown')}"
                text = utterance['text']
                
                vtt_lines.append(f"{start_time} --> {end_time}\n")
                vtt_lines.append(f"<v {speaker}>{text}\n\n")
        else:
            # Fallback to words if no utterances
            words = assemblyai_data.get('words', [])
            if words:
                # Group words into sentences
                current_sentence = []
                sentence_start = 0
                
                for word in words:
                    current_sentence.append(word['text'])
                    
                    if not sentence_start:
                        sentence_start = word['start']
                    
                    # End sentence on punctuation
                    if word['text'][-1] in '.!?':
                        start_time = self.ms_to_vtt_timestamp(sentence_start)
                        end_time = self.ms_to_vtt_timestamp(word['end'])
                        text = ' '.join(current_sentence)
                        
                        vtt_lines.append(f"{start_time} --> {end_time}\n")
                        vtt_lines.append(f"{text}\n\n")
                        
                        current_sentence = []
                        sentence_start = 0
        
        return ''.join(vtt_lines)
    
    def ms_to_vtt_timestamp(self, ms):
        """Convert milliseconds to VTT timestamp format"""
        seconds = ms / 1000
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"
    
    def save_error(self, task_id, error):
        """Save error state"""
        result_file = f"/tmp/result_{task_id}.json"
        with open(result_file, 'w') as f:
            json.dump({
                'success': False,
                'task_id': task_id,
                'status': 'failed',
                'error': error
            }, f)
    
    def do_GET(self):
        """Health check"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = {'status': 'ready', 'service': 'DozentenFeedback-Callback'}
        self.wfile.write(json.dumps(response).encode())