"""Audio transcription module using AssemblyAI."""

import logging
from pathlib import Path
from typing import Optional

import assemblyai as aai
import ffmpeg

from .config import ASSEMBLYAI_API_KEY

logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """Custom exception for transcription errors."""

    pass


class AudioTranscriber:
    """Handles audio transcription using AssemblyAI."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize transcriber with API key."""

        self.api_key = api_key or ASSEMBLYAI_API_KEY
        if not self.api_key:
            raise TranscriptionError(
                "AssemblyAI API key not found. Please set ASSEMBLYAI_API_KEY in .env file."
            )

        aai.settings.api_key = self.api_key

        # Configure transcription settings for lectures
        self.config = aai.TranscriptionConfig(
            speech_model=aai.SpeechModel.universal, speaker_labels=True, language_code="de"
        )

        self.transcriber = aai.Transcriber(config=self.config)

    def convert_mp4_to_wav(self, mp4_path: Path) -> Path:
        """
        Convert MP4 to WAV using ffmpeg-python.

        Args:
            mp4_path: Path to input MP4 file

        Returns:
            Path to generated WAV file

        Raises:
            TranscriptionError: If conversion fails
        """
        try:
            # Create output path with .wav extension
            output_path = mp4_path.with_suffix(".wav")

            # Check if ffmpeg is available
            try:
                ffmpeg.probe(str(mp4_path))
            except ffmpeg.Error as e:
                if "ffmpeg" in str(e).lower() and "not found" in str(e).lower():
                    raise TranscriptionError(
                        "FFmpeg not found. Please install FFmpeg:\n"
                        "  macOS: brew install ffmpeg\n"
                        "  Linux: sudo apt-get install ffmpeg\n"
                        "  Windows: Download from https://ffmpeg.org"
                    ) from e
                raise

            logger.info(f"Converting {mp4_path} to WAV format...")

            # Convert MP4 to WAV with 16kHz sample rate
            stream = ffmpeg.input(str(mp4_path))
            stream = ffmpeg.output(
                stream,
                str(output_path),
                acodec="pcm_s16le",  # 16-bit PCM
                ar=16000,  # 16kHz sample rate
                ac=1,  # Mono audio
            )

            ffmpeg.run(stream, overwrite_output=True, quiet=True)

            logger.info(f"Successfully converted to {output_path}")
            return output_path

        except ffmpeg.Error as e:
            raise TranscriptionError(f"Failed to convert MP4 to WAV: {e}") from e
        except Exception as e:
            raise TranscriptionError(f"Unexpected error during MP4 conversion: {e}") from e

    def transcribe_audio(self, audio_path: Path) -> str:
        """
        Transcribe audio file using AssemblyAI.

        Args:
            audio_path: Path to audio file (WAV, MP3, MP4, etc.)

        Returns:
            VTT-formatted transcription with timestamps

        Raises:
            TranscriptionError: If transcription fails
        """
        try:
            logger.info(f"Starting transcription of {audio_path}...")

            # Upload and transcribe
            transcript = self.transcriber.transcribe(str(audio_path))

            # Check transcription status
            if transcript.status == "error":
                raise TranscriptionError(f"Transcription failed: {transcript.error}")

            logger.info("Transcription completed successfully")

            # Export as VTT format with timestamps
            vtt_content = transcript.export_subtitles_vtt()

            if not vtt_content:
                raise TranscriptionError("Generated VTT content is empty")

            return vtt_content

        except Exception as e:
            if isinstance(e, TranscriptionError):
                raise
            raise TranscriptionError(f"Transcription failed: {e}") from e

    def process_audio_file(self, file_path: Path) -> str:
        """
        Process audio/video file and return VTT transcription.

        Handles both direct audio files and MP4 conversion.

        Args:
            file_path: Path to audio or video file

        Returns:
            VTT-formatted transcription

        Raises:
            TranscriptionError: If processing fails
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise TranscriptionError(f"File not found: {file_path}")

        suffix = file_path.suffix.lower()

        if suffix == ".mp4":
            logger.info("Processing MP4 file - converting to WAV first...")

            # Convert MP4 to WAV
            wav_path = self.convert_mp4_to_wav(file_path)

            try:
                # Transcribe the WAV file
                vtt_content = self.transcribe_audio(wav_path)

                # Clean up temporary WAV file
                if wav_path != file_path and wav_path.exists():
                    wav_path.unlink()
                    logger.info(f"Cleaned up temporary file: {wav_path}")

                return vtt_content

            except Exception:
                # Clean up on error
                if wav_path != file_path and wav_path.exists():
                    wav_path.unlink()
                raise

        elif suffix in [".wav", ".mp3", ".m4a", ".flac", ".aac"]:
            logger.info(f"Processing {suffix} audio file...")
            return self.transcribe_audio(file_path)

        else:
            raise TranscriptionError(
                f"Unsupported audio format: {suffix}. "
                f"Supported formats: .mp4, .wav, .mp3, .m4a, .flac, .aac"
            )


def transcribe_file(file_path: Path, api_key: Optional[str] = None) -> str:
    """
    Convenience function to transcribe an audio/video file.

    Args:
        file_path: Path to audio or video file
        api_key: Optional AssemblyAI API key

    Returns:
        VTT-formatted transcription

    Raises:
        TranscriptionError: If transcription fails
    """
    transcriber = AudioTranscriber(api_key=api_key)
    return transcriber.process_audio_file(file_path)


def check_transcription_dependencies() -> bool:
    """
    Check if transcription dependencies are available.

    Returns:
        True if dependencies are available, False otherwise
    """
    try:
        # Check if required modules and API key are available
        import assemblyai as aai  # noqa: F401
        import ffmpeg  # noqa: F401

        return bool(ASSEMBLYAI_API_KEY)
    except ImportError:
        return False


def get_supported_audio_formats() -> list[str]:
    """
    Get list of supported audio/video formats.

    Returns:
        List of supported file extensions
    """
    return [".mp4", ".wav", ".mp3", ".m4a", ".flac", ".aac"]
