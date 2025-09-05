"""VTT (WebVTT) parser for extracting timestamped transcription data."""

import re
from dataclasses import dataclass
from typing import Any, Optional, Tuple

import webvtt


@dataclass
class VTTEntry:
    """Represents a single VTT subtitle entry."""

    start_seconds: float
    end_seconds: float
    text: str
    speaker: Optional[str] = None


class VTTParser:
    """Parser for WebVTT subtitle files using webvtt-py library."""

    def __init__(self) -> None:
        """Initialize VTT parser."""
        # Pattern for speaker detection in subtitle text
        self.speaker_patterns = [
            re.compile(r"^Speaker\s+([A-Z]):\s*(.*)$", re.IGNORECASE),
            re.compile(r"^([A-Z]):\s*(.*)$"),
            re.compile(r"^\[([^\]]+)\]:\s*(.*)$"),
        ]

    def extract_speaker(self, text: str) -> Tuple[Optional[str], str]:
        """
        Extract speaker information from subtitle text.

        Args:
            text: Subtitle text that might contain speaker info

        Returns:
            Tuple of (speaker_name, cleaned_text)
        """
        for pattern in self.speaker_patterns:
            match = pattern.match(text.strip())
            if match:
                speaker = match.group(1)
                cleaned_text = match.group(2).strip()
                return speaker, cleaned_text

        # No speaker pattern found
        return None, text.strip()

    def parse_vtt_content(self, vtt_content: str) -> list[VTTEntry]:
        """
        Parse VTT content from a string and extract all subtitle entries.

        Args:
            vtt_content: VTT formatted string content

        Returns:
            List of VTTEntry objects
        """
        import tempfile
        import os
        
        # Write content to temporary file for webvtt-py
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vtt', delete=False) as tmp_file:
            tmp_file.write(vtt_content)
            tmp_path = tmp_file.name
        
        try:
            entries = self.parse_vtt_file(tmp_path)
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        
        return entries

    def parse_vtt_file(self, file_path: str) -> list[VTTEntry]:
        """
        Parse a VTT file and extract all subtitle entries using webvtt-py.

        Args:
            file_path: Path to the VTT file

        Returns:
            List of VTTEntry objects
        """
        try:
            vtt = webvtt.read(file_path)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"VTT file not found: {file_path}") from e
        except Exception as e:
            raise OSError(f"Error reading VTT file: {e}") from e

        entries = []

        for caption in vtt:
            # Extract speaker information
            speaker, clean_text = self.extract_speaker(caption.text)

            # Convert start and end times to seconds
            start_seconds = self._time_to_seconds(caption.start)
            end_seconds = self._time_to_seconds(caption.end)

            entry = VTTEntry(
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                text=clean_text,
                speaker=speaker,
            )
            entries.append(entry)

        return entries

    def _time_to_seconds(self, time_str: str) -> float:
        """
        Convert webvtt-py time string to seconds.

        Args:
            time_str: Time string from webvtt-py (e.g., "00:01:36.190")

        Returns:
            Total seconds as float
        """
        try:
            # webvtt-py returns times in HH:MM:SS.mmm format always
            time_parts = time_str.split(":")
            hours = int(time_parts[0])
            minutes = int(time_parts[1])
            seconds_with_ms = float(time_parts[2])

            return hours * 3600 + minutes * 60 + seconds_with_ms

        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid time format: {time_str}") from e

    def group_by_time_blocks(
        self, entries: list[VTTEntry], block_duration_minutes: int = 30
    ) -> list[dict[str, Any]]:
        """
        Group VTT entries into time blocks of specified duration.

        Args:
            entries: List of VTTEntry objects
            block_duration_minutes: Duration of each block in minutes

        Returns:
            List of dictionaries containing block information
        """
        if not entries:
            return []

        block_duration_seconds = block_duration_minutes * 60
        blocks = []

        # Find the start time of first entry
        # start_time = entries[0].start_seconds  # Keep for reference but not used
        block_number = 1

        # Calculate total duration based on last entry
        total_duration = entries[-1].end_seconds if entries else 0

        # Create blocks
        current_block_start = 0
        while current_block_start < total_duration:
            current_block_end = current_block_start + block_duration_seconds

            # Collect entries that fall within this time block
            block_entries = [
                entry
                for entry in entries
                if (
                    entry.start_seconds >= current_block_start
                    and entry.start_seconds < current_block_end
                )
            ]

            if block_entries:
                # Format time ranges
                start_time_str = self.seconds_to_time_string(current_block_start)
                end_time_str = self.seconds_to_time_string(current_block_end)

                # Combine text from all entries in this block
                block_text_parts = []
                current_speaker = None

                for entry in block_entries:
                    if entry.speaker and entry.speaker != current_speaker:
                        # New speaker
                        current_speaker = entry.speaker
                        block_text_parts.append(f"Speaker {entry.speaker}: {entry.text}")
                    elif entry.speaker:
                        # Same speaker continues
                        block_text_parts.append(entry.text)
                    else:
                        # No speaker info
                        block_text_parts.append(entry.text)

                block_info = {
                    "block_number": block_number,
                    "start_time": start_time_str,
                    "end_time": end_time_str,
                    "start_seconds": current_block_start,
                    "end_seconds": current_block_end,
                    "content": " ".join(block_text_parts),
                    "entry_count": len(block_entries),
                    "entries": block_entries,
                }

                blocks.append(block_info)
                block_number += 1

            current_block_start = current_block_end

        return blocks

    def seconds_to_time_string(self, seconds: float) -> str:
        """
        Convert seconds to HH:MM format for display.

        Args:
            seconds: Time in seconds

        Returns:
            Time string in HH:MM format
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours:02d}:{minutes:02d}"

    def get_total_duration(self, entries: list[VTTEntry]) -> float:
        """
        Get total duration of the transcription in seconds.

        Args:
            entries: List of VTTEntry objects

        Returns:
            Total duration in seconds
        """
        if not entries:
            return 0.0

        return entries[-1].end_seconds
