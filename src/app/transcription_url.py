"""
Extended transcription module for handling URLs.
"""

import os
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import httpx

import assemblyai as aai
from .transcription import TranscriptionError

def transcribe_from_url(url: str, api_key: Optional[str] = None, metadata: Dict[str, Any] = None) -> str:
    """
    Transcribe video/audio from URL using AssemblyAI.
    Handles Zoom URLs which may require special processing.
    
    Args:
        url: Direct URL to video/audio file (Zoom or other)
        api_key: AssemblyAI API key (optional, will use env var if not provided)
        metadata: Optional metadata about the recording
    
    Returns:
        VTT formatted transcription
    
    Raises:
        TranscriptionError: If transcription fails
    """
    api_key = api_key or os.environ.get("ASSEMBLYAI_API_KEY")
    
    if not api_key:
        raise TranscriptionError("AssemblyAI API key not found")
    
    # Configure AssemblyAI
    aai.settings.api_key = api_key
    
    try:
        # For Zoom URLs, we might need to handle redirects differently
        is_zoom_url = 'zoom.us' in url or 'zoom.com' in url
        
        if is_zoom_url:
            print(f"Detected Zoom URL, checking accessibility...")
            # Zoom URLs often work directly with AssemblyAI
            # but we should verify first
            with httpx.Client(follow_redirects=True) as client:
                try:
                    response = client.head(url, timeout=10.0)
                    print(f"Zoom URL status: {response.status_code}")
                except Exception as e:
                    print(f"Note: Could not verify Zoom URL (this is often normal): {e}")
        
        # Create transcriber
        transcriber = aai.Transcriber()
        
        # Configure transcription with optimal settings for meetings
        config = aai.TranscriptionConfig(
            language_detection=True,
            speaker_labels=True,  # Important for meetings
            auto_chapters=True,
            entity_detection=True,
            format_text=True,
            punctuate=True,
            disfluencies=False,  # Remove um, uh, etc.
            speech_threshold=0.5  # Adjust for meeting audio quality
        )
        
        # Add meeting-specific processing if metadata provided
        if metadata:
            print(f"Processing meeting: {metadata.get('topic', 'Unknown')}")
            print(f"Duration: {metadata.get('duration', 'Unknown')} minutes")
        
        # Transcribe from URL
        print(f"Starting transcription with AssemblyAI...")
        print(f"URL: {url[:100]}...")  # Log first 100 chars for debugging
        
        transcript = transcriber.transcribe(url, config=config)
        
        # Wait for completion (AssemblyAI handles this internally)
        print(f"Transcription status: {transcript.status}")
        
        if transcript.error:
            raise TranscriptionError(f"AssemblyAI error: {transcript.error}")
        
        # Export as VTT with timestamps
        vtt_content = transcript.export_subtitles_vtt()
        
        if not vtt_content:
            raise TranscriptionError("Failed to generate VTT subtitles")
        
        # Add metadata as VTT NOTE if provided
        if metadata and metadata.get('topic'):
            vtt_header = f"WEBVTT\nNOTE\nMeeting: {metadata.get('topic')}\nDuration: {metadata.get('duration', 'N/A')} minutes\n\n"
            if vtt_content.startswith("WEBVTT"):
                vtt_content = vtt_content.replace("WEBVTT", vtt_header, 1)
        
        print(f"Transcription completed successfully")
        return vtt_content
        
    except Exception as e:
        if isinstance(e, TranscriptionError):
            raise
        raise TranscriptionError(f"Failed to transcribe from URL: {str(e)}")


def download_video_to_temp(url: str, max_size_mb: int = 500) -> Path:
    """
    Download video to temporary file with size limit.
    
    Args:
        url: Video URL
        max_size_mb: Maximum file size in MB
    
    Returns:
        Path to downloaded file
    
    Raises:
        TranscriptionError: If download fails or file too large
    """
    try:
        with httpx.Client() as client:
            # Check file size first
            response = client.head(url, follow_redirects=True)
            content_length = int(response.headers.get('content-length', 0))
            
            if content_length > max_size_mb * 1024 * 1024:
                raise TranscriptionError(f"File too large: {content_length / 1024 / 1024:.1f} MB")
            
            # Download file
            response = client.get(url, follow_redirects=True, timeout=300.0)
            response.raise_for_status()
            
            # Save to temp file
            suffix = Path(urlparse(url).path).suffix or '.mp4'
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_file:
                tmp_file.write(response.content)
                return Path(tmp_file.name)
                
    except Exception as e:
        raise TranscriptionError(f"Failed to download video: {str(e)}")