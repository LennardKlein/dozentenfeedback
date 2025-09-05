#!/usr/bin/env python3
"""
Process a Zoom video URL directly
Can be run standalone or receive webhooks
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')
load_dotenv('.env')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def process_video(video_url, metadata=None):
    """Process a video and return results"""
    
    from app.transcription_url import transcribe_from_url
    from app.chunker import TranscriptionChunker
    from app.analyzer import LectureAnalyzer
    from app.aggregator import ScoreAggregator
    from app.formatter import MarkdownFormatter
    
    print("\n" + "="*60)
    print("🚀 STARTING VIDEO PROCESSING")
    print("="*60)
    
    # Create output directory
    output_dir = Path("debug_output")
    output_dir.mkdir(exist_ok=True)
    
    try:
        # Step 1: Transcribe
        print("\n📝 Step 1: Transcribing with AssemblyAI...")
        print(f"Video URL: {video_url[:100]}...")
        if metadata:
            print(f"Meeting: {metadata.get('topic', 'Unknown')}")
            print(f"Duration: {metadata.get('duration', 'Unknown')} minutes")
        
        print("\nThis will take 2-5 minutes depending on video length...")
        vtt_content = transcribe_from_url(video_url, metadata=metadata)
        
        print(f"✅ Transcription complete: {len(vtt_content)} characters")
        
        # Save transcription
        vtt_path = output_dir / "last_transcription.vtt"
        with open(vtt_path, "w") as f:
            f.write(vtt_content)
        print(f"💾 Saved to: {vtt_path}")
        
        # Step 2: Chunk
        print("\n✂️  Step 2: Chunking transcription...")
        chunker = TranscriptionChunker()
        blocks = chunker.chunk_from_vtt_content(vtt_content)
        print(f"✅ Created {len(blocks)} blocks")
        
        # Step 3: Analyze
        print("\n🧠 Step 3: Analyzing with OpenAI...")
        analyzer = LectureAnalyzer()
        block_analyses = []
        
        for i, block in enumerate(blocks):
            print(f"   Analyzing block {i+1}/{len(blocks)}...")
            analysis = analyzer.analyze_block(block)
            block_analyses.append(analysis)
        
        # Step 4: Aggregate
        print("\n📊 Step 4: Aggregating results...")
        aggregator = ScoreAggregator()
        complete_report = aggregator.create_complete_report(block_analyses)
        
        # Step 5: Format
        print("\n📄 Step 5: Generating report...")
        formatter = MarkdownFormatter()
        markdown_report = formatter.format_complete_report(complete_report)
        kurzfassung = formatter.format_kurzfassung(complete_report)
        
        # Save reports
        report_path = output_dir / "last_report.md"
        with open(report_path, "w") as f:
            f.write(markdown_report)
        print(f"💾 Full report saved to: {report_path}")
        
        summary_path = output_dir / "last_summary.md"
        with open(summary_path, "w") as f:
            f.write(kurzfassung)
        print(f"💾 Summary saved to: {summary_path}")
        
        print("\n" + "="*60)
        print("🎉 PROCESSING COMPLETE!")
        print("="*60)
        print(f"📊 Overall Score: {complete_report.overall_score}/5")
        print(f"📦 Blocks Analyzed: {len(blocks)}")
        print(f"\n📁 Check the 'debug_output' folder for:")
        print(f"   - {vtt_path.name} (transcription)")
        print(f"   - {report_path.name} (full analysis)")
        print(f"   - {summary_path.name} (executive summary)")
        
        return {
            'success': True,
            'overall_score': complete_report.overall_score,
            'blocks_analyzed': len(blocks),
            'output_dir': str(output_dir.absolute())
        }
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }

def main():
    """Run as standalone script or with webhook data"""
    
    if len(sys.argv) > 1:
        # Run with command line argument
        video_url = sys.argv[1]
        print(f"Processing video from command line: {video_url}")
        process_video(video_url)
    else:
        # Use the test Zoom URL from your webhook
        print("Using test Zoom video URL...")
        video_url = "https://zoom.us/rec/download/_FbHNjXaLU3UJ50uOW7xjocuO6qUHp3Lry3Q_DdtZXrza2Zn4OvR7oSNlja73_zSVl9bHaGNIq9h1_1I.K1ZplQQurTpRfbsz"
        
        metadata = {
            'topic': 'Karriere-Insights & Best Practices',
            'host_email': 'admin@talentspring-academy.com',
            'duration': '71'
        }
        
        print("Processing Zoom recording...")
        print(f"Topic: {metadata['topic']}")
        print(f"Duration: {metadata['duration']} minutes")
        
        result = process_video(video_url, metadata)
        
        if result['success']:
            print(f"\n✅ Success! Check {result['output_dir']}")
        else:
            print(f"\n❌ Failed: {result.get('error')}")

if __name__ == "__main__":
    main()