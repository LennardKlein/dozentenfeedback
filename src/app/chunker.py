"""Text chunking module for splitting transcriptions into analyzable blocks."""

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import tiktoken

from .config import CHUNK_DURATION_MINUTES, MAX_TOKENS_PER_CHUNK
from .models import TimeBlock
from .vtt_parser import VTTParser


class TranscriptionChunker:
    """Handles chunking of transcription text into time-based blocks."""

    def __init__(self, model_name: str = "gpt-4o"):
        """Initialize with tiktoken encoder for token counting."""
        try:
            self.encoder = tiktoken.encoding_for_model(model_name)
        except KeyError:
            # Fallback to cl100k_base encoding if model not found
            self.encoder = tiktoken.get_encoding("cl100k_base")

        self.vtt_parser = VTTParser()

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self.encoder.encode(text))

    def extract_timestamps(self, content: str) -> list[tuple[str, str]]:
        """
        Extract timestamp patterns from transcription content.

        Expected formats:
        - HH:MM format (e.g., "09:30")
        - Speaker timestamps
        - Block indicators

        Returns list of (timestamp, text) tuples.
        """
        # Pattern for timestamps like "09:30" or timestamps in speaker labels
        timestamp_patterns = [
            r"\b(\d{2}:\d{2})\b",  # HH:MM format
            r"(\d{1,2}:\d{2})",  # H:MM or HH:MM
        ]

        timestamps = []
        lines = content.split("\n")

        for line in lines:
            for pattern in timestamp_patterns:
                matches = re.findall(pattern, line.strip())
                if matches:
                    # Take the first timestamp found in the line
                    timestamp = matches[0]
                    timestamps.append((timestamp, line.strip()))
                    break

        return timestamps

    def parse_time(self, time_str: str) -> datetime:
        """Parse time string to datetime object (using today's date)."""
        try:
            # Handle both H:MM and HH:MM formats
            if ":" in time_str:
                time_parts = time_str.split(":")
                hour = int(time_parts[0])
                minute = int(time_parts[1])

                # Use today's date with the extracted time
                return datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        except (ValueError, IndexError):
            pass

        # Fallback: return current time
        return datetime.now()

    def create_time_based_blocks(self, content: str) -> list[TimeBlock]:
        """
        Create time-based blocks from transcription content.

        Attempts to detect timestamps and create 30-minute blocks.
        Falls back to character-based chunking if no timestamps found.
        """
        timestamps = self.extract_timestamps(content)

        if not timestamps:
            return self.create_fallback_blocks(content)

        blocks = []
        block_number = 1

        # Sort timestamps by time
        sorted_timestamps = []
        for ts, line in timestamps:
            try:
                dt = self.parse_time(ts)
                sorted_timestamps.append((dt, ts, line))
            except (ValueError, AttributeError):
                # Skip invalid timestamps
                continue

        if not sorted_timestamps:
            return self.create_fallback_blocks(content)

        sorted_timestamps.sort(key=lambda x: x[0])

        # Group content by 30-minute intervals
        start_time = sorted_timestamps[0][0]
        current_block_start = start_time
        current_block_content: list[str] = []

        for dt, _ts, line in sorted_timestamps:
            # Check if we should start a new block
            if dt >= current_block_start + timedelta(minutes=CHUNK_DURATION_MINUTES):
                # Create block with accumulated content
                if current_block_content:
                    block_end = current_block_start + timedelta(minutes=CHUNK_DURATION_MINUTES)
                    blocks.append(
                        TimeBlock(
                            block_number=block_number,
                            start_time=current_block_start.strftime("%H:%M"),
                            end_time=block_end.strftime("%H:%M"),
                            content="\n".join(current_block_content),
                        )
                    )
                    block_number += 1

                # Start new block
                current_block_start = dt
                current_block_content = [line]
            else:
                current_block_content.append(line)

        # Add final block
        if current_block_content:
            block_end = current_block_start + timedelta(minutes=CHUNK_DURATION_MINUTES)
            blocks.append(
                TimeBlock(
                    block_number=block_number,
                    start_time=current_block_start.strftime("%H:%M"),
                    end_time=block_end.strftime("%H:%M"),
                    content="\n".join(current_block_content),
                )
            )

        return blocks

    def create_fallback_blocks(self, content: str) -> list[TimeBlock]:
        """
        Create blocks based on content length when no timestamps available.

        Splits content to stay under token limits while preserving context.
        """
        blocks = []
        lines = content.split("\n")
        block_number = 1
        current_block: list[str] = []
        current_tokens = 0

        for line in lines:
            line_tokens = self.count_tokens(line)

            # If adding this line would exceed token limit, create new block
            if current_tokens + line_tokens > MAX_TOKENS_PER_CHUNK and current_block:
                block_content = "\n".join(current_block)
                blocks.append(
                    TimeBlock(
                        block_number=block_number,
                        start_time=f"Block {block_number} Start",
                        end_time=f"Block {block_number} End",
                        content=block_content,
                    )
                )

                # Start new block
                block_number += 1
                current_block = [line]
                current_tokens = line_tokens
            else:
                current_block.append(line)
                current_tokens += line_tokens

        # Add final block
        if current_block:
            block_content = "\n".join(current_block)
            blocks.append(
                TimeBlock(
                    block_number=block_number,
                    start_time=f"Block {block_number} Start",
                    end_time=f"Block {block_number} End",
                    content=block_content,
                )
            )

        return blocks

    def chunk_from_vtt(self, vtt_file_path: str) -> list[TimeBlock]:
        """
        Create time-based blocks from VTT file with accurate timestamps.

        Args:
            vtt_file_path: Path to the VTT file

        Returns:
            List of TimeBlock objects with accurate time ranges
        """
        try:
            # Parse VTT file
            vtt_entries = self.vtt_parser.parse_vtt_file(vtt_file_path)
            if not vtt_entries:
                return []

            # Group entries into 30-minute blocks
            time_blocks = self.vtt_parser.group_by_time_blocks(vtt_entries, CHUNK_DURATION_MINUTES)

            # Convert to TimeBlock objects
            blocks = []
            for block_info in time_blocks:
                # Validate token count
                content = block_info["content"]
                tokens = self.count_tokens(content)

                if tokens <= MAX_TOKENS_PER_CHUNK:
                    blocks.append(
                        TimeBlock(
                            block_number=block_info["block_number"],
                            start_time=block_info["start_time"],
                            end_time=block_info["end_time"],
                            content=content,
                        )
                    )
                else:
                    # Split large blocks if needed
                    sub_blocks = self._split_vtt_block(block_info)
                    blocks.extend(sub_blocks)

            return blocks

        except Exception as e:
            print(f"Warning: Failed to parse VTT file {vtt_file_path}: {e}")
            return []

    def chunk_transcription(
        self, content: str, vtt_file_path: Optional[str] = None
    ) -> list[TimeBlock]:
        """
        Main method to chunk transcription content.

        Args:
            content: Raw transcription text
            vtt_file_path: Optional path to VTT file for accurate timestamps

        Returns:
            List of TimeBlock objects ready for analysis
        """
        if not content.strip():
            return []

        # Try VTT-based chunking first if VTT file is provided
        if vtt_file_path and Path(vtt_file_path).exists():
            vtt_blocks = self.chunk_from_vtt(vtt_file_path)
            if vtt_blocks:
                return vtt_blocks

        # Fall back to text-based chunking
        blocks = self.create_time_based_blocks(content)

        # Validate blocks aren't too large
        validated_blocks = []
        for block in blocks:
            tokens = self.count_tokens(block.content)
            if tokens <= MAX_TOKENS_PER_CHUNK:
                validated_blocks.append(block)
            else:
                # Split large blocks further
                sub_blocks = self._split_large_block(block)
                validated_blocks.extend(sub_blocks)

        return validated_blocks

    def chunk_from_vtt_content(self, vtt_content: str) -> list[TimeBlock]:
        """
        Create time-based blocks from VTT content string.

        Args:
            vtt_content: VTT formatted content

        Returns:
            List of TimeBlock objects with accurate time ranges
        """
        try:
            # Parse VTT content
            vtt_entries = self.vtt_parser.parse_vtt_content(vtt_content)
            if not vtt_entries:
                return []

            # Group entries into 30-minute blocks
            time_blocks = self.vtt_parser.group_by_time_blocks(vtt_entries, CHUNK_DURATION_MINUTES)

            # Convert to TimeBlock objects
            blocks = []
            for block_info in time_blocks:
                # Validate token count
                content = block_info["content"]
                tokens = self.count_tokens(content)

                if tokens <= MAX_TOKENS_PER_CHUNK:
                    blocks.append(
                        TimeBlock(
                            block_number=block_info["block_number"],
                            start_time=block_info["start_time"],
                            end_time=block_info["end_time"],
                            content=content,
                        )
                    )
                else:
                    # Split large blocks if needed
                    sub_blocks = self._split_vtt_block(block_info)
                    blocks.extend(sub_blocks)

            return blocks

        except Exception as e:
            print(f"Warning: Failed to parse VTT content: {e}")
            return []

    def chunk_from_file(self, file_path: str) -> list[TimeBlock]:
        """
        Chunk transcription from file, auto-detecting format.

        Args:
            file_path: Path to transcription file (.txt or .vtt)

        Returns:
            List of TimeBlock objects
        """
        path_obj = Path(file_path)

        if not path_obj.exists():
            raise FileNotFoundError(f"File not found: {path_obj}")

        # Handle VTT files directly
        if path_obj.suffix.lower() == ".vtt":
            return self.chunk_from_vtt(str(path_obj))

        # Handle text files
        if path_obj.suffix.lower() == ".txt":
            with open(path_obj, encoding="utf-8") as f:
                content = f.read()

            # Look for matching VTT file
            vtt_file = path_obj.with_suffix(".vtt")
            vtt_path = str(vtt_file) if vtt_file.exists() else None

            return self.chunk_transcription(content, vtt_path)

        raise ValueError(f"Unsupported file format: {path_obj.suffix}")

    def _split_vtt_block(self, block_info: dict[str, Any]) -> list[TimeBlock]:
        """Split a VTT-based block that's too large into smaller sub-blocks."""
        entries = block_info["entries"]
        sub_blocks = []
        sub_block_number = 1
        current_entries: list[Any] = []
        current_tokens = 0

        for entry in entries:
            entry_text = f"Speaker {entry.speaker}: {entry.text}" if entry.speaker else entry.text
            entry_tokens = self.count_tokens(entry_text)

            if current_tokens + entry_tokens > MAX_TOKENS_PER_CHUNK and current_entries:
                # Create sub-block
                content = " ".join(
                    [
                        f"Speaker {e.speaker}: {e.text}" if e.speaker else e.text
                        for e in current_entries
                    ]
                )

                start_time = self.vtt_parser.seconds_to_time_string(
                    current_entries[0].start_seconds
                )
                end_time = self.vtt_parser.seconds_to_time_string(current_entries[-1].end_seconds)

                sub_blocks.append(
                    TimeBlock(
                        block_number=f"{block_info['block_number']}.{sub_block_number}",
                        start_time=f"{start_time} (part {sub_block_number})",
                        end_time=f"{end_time} (part {sub_block_number})",
                        content=content,
                    )
                )

                sub_block_number += 1
                current_entries = [entry]
                current_tokens = entry_tokens
            else:
                current_entries.append(entry)
                current_tokens += entry_tokens

        # Add final sub-block
        if current_entries:
            content = " ".join(
                [f"Speaker {e.speaker}: {e.text}" if e.speaker else e.text for e in current_entries]
            )

            start_time = self.vtt_parser.seconds_to_time_string(current_entries[0].start_seconds)
            end_time = self.vtt_parser.seconds_to_time_string(current_entries[-1].end_seconds)

            sub_blocks.append(
                TimeBlock(
                    block_number=f"{block_info['block_number']}.{sub_block_number}",
                    start_time=f"{start_time} (part {sub_block_number})",
                    end_time=f"{end_time} (part {sub_block_number})",
                    content=content,
                )
            )

        return sub_blocks

    def _split_large_block(self, block: TimeBlock) -> list[TimeBlock]:
        """Split a block that's too large into smaller sub-blocks."""
        lines = block.content.split("\n")
        sub_blocks = []
        sub_block_number = 1
        current_lines: list[str] = []
        current_tokens = 0

        for line in lines:
            line_tokens = self.count_tokens(line)

            if current_tokens + line_tokens > MAX_TOKENS_PER_CHUNK and current_lines:
                # Create sub-block
                sub_blocks.append(
                    TimeBlock(
                        block_number=f"{block.block_number}.{sub_block_number}",
                        start_time=f"{block.start_time} (part {sub_block_number})",
                        end_time=f"{block.end_time} (part {sub_block_number})",
                        content="\n".join(current_lines),
                    )
                )

                sub_block_number += 1
                current_lines = [line]
                current_tokens = line_tokens
            else:
                current_lines.append(line)
                current_tokens += line_tokens

        # Add final sub-block
        if current_lines:
            sub_blocks.append(
                TimeBlock(
                    block_number=f"{block.block_number}.{sub_block_number}",
                    start_time=f"{block.start_time} (part {sub_block_number})",
                    end_time=f"{block.end_time} (part {sub_block_number})",
                    content="\n".join(current_lines),
                )
            )

        return sub_blocks
