from typing import Optional
"""Main CLI module for the Dozenten Feedback Analysis System."""

import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .aggregator import ScoreAggregator
from .analyzer import LectureAnalyzer
from .chunker import TranscriptionChunker
from .config import ASSEMBLYAI_API_KEY, OPENAI_API_KEY
from .formatter import MarkdownFormatter
from .models import CompleteReport, TimeBlock
from .transcription import (
    TranscriptionError,
    check_transcription_dependencies,
    get_supported_audio_formats,
    transcribe_file,
)

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

console = Console()


@click.command()
@click.option(
    "--input",
    "-i",
    required=True,
    type=click.Path(exists=True),
    help="Path to input file (.txt, .vtt, .wav, .mp3, .mp4, .m4a, .flac, .aac)",
)
@click.option(
    "--output", "-o", type=click.Path(), help="Output file path (default: analysis_TIMESTAMP.md)"
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["markdown", "json", "both"]),
    default="markdown",
    help="Output format",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--dry-run", is_flag=True, help="Show analysis plan without calling OpenAI API")
def main(input: str, output: Optional[str], format: str, verbose: bool, dry_run: bool) -> None:
    """
    Analyze lecture transcriptions using OpenAI API.

    This tool supports multiple input formats:
    - Audio/Video: .mp4, .wav, .mp3, .m4a, .flac, .aac (transcribed via AssemblyAI)
    - Text: .vtt (subtitles with timestamps), .txt (plain text)

    VTT files and audio/video files are preferred as they provide accurate timestamps
    for proper 30-minute chunking.

    For audio/video files, you need:
    - AssemblyAI API key in .env file
    - FFmpeg installed (for MP4 processing)
    """

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Check API key
    if not OPENAI_API_KEY and not dry_run:
        console.print(
            "[red]Error: OpenAI API key not found. Please set OPENAI_API_KEY in .env file.[/red]"
        )
        sys.exit(1)

    try:
        # Check input file
        input_path = Path(input)
        console.print(f"[blue]Reading transcription file: {input_path.name}[/blue]")

        # Determine file type and processing approach
        file_extension = input_path.suffix.lower()
        audio_formats = get_supported_audio_formats()
        needs_transcription = file_extension in audio_formats

        if needs_transcription:
            # Audio/video file processing
            console.print(f"[green]✓[/green] Audio/video file detected: {file_extension}")

            # Check dependencies and API keys for audio/video files
            if not check_transcription_dependencies():
                console.print("[red]Error: Missing transcription dependencies.[/red]")
                console.print("Please install: [bold]pip install assemblyai ffmpeg-python[/bold]")
                console.print("Also ensure the ENV var [bold]ASSEMBLY_AI_API_KEY[/bold] is set.")
                sys.exit(1)

            if not ASSEMBLYAI_API_KEY and not dry_run:
                console.print("[red]Error: AssemblyAI API key not found.[/red]")
                console.print("Please set [bold]ASSEMBLYAI_API_KEY[/bold] in .env file.")
                sys.exit(1)

            if file_extension == ".mp4":
                console.print(
                    "[yellow]Note: MP4 processing requires FFmpeg to be installed.[/yellow]"
                )

            if not dry_run:
                # Transcribe audio/video file to VTT
                console.print(
                    f"[yellow]🎵 Transcribing {file_extension} file using AssemblyAI...[/yellow]"
                )
                with console.status("[bold yellow]Transcribing audio..."):
                    try:
                        vtt_content = transcribe_file(input_path)

                        # Save transcription for reference
                        transcription_path = input_path.with_suffix(".vtt")
                        with open(transcription_path, "w", encoding="utf-8") as f:
                            f.write(vtt_content)

                        console.print(f"[green]✓[/green] Transcription saved: {transcription_path}")

                        # Use the transcribed VTT for processing
                        input_for_processing = transcription_path

                    except TranscriptionError as e:
                        console.print(f"[red]Transcription failed: {e}[/red]")
                        sys.exit(1)
            else:
                # In dry run mode, simulate the process
                input_for_processing = input_path
                console.print("[yellow]Dry run: Would transcribe audio file to VTT format[/yellow]")

        elif file_extension == ".vtt":
            console.print(
                "[green]✓[/green] VTT file detected - using accurate timestamps for chunking"
            )
            input_for_processing = input_path

        elif file_extension == ".txt":
            vtt_file = input_path.with_suffix(".vtt")
            if vtt_file.exists():
                console.print(f"[green]✓[/green] Found matching VTT file: {vtt_file.name}")
                input_for_processing = vtt_file
            else:
                console.print(
                    "[yellow]⚠[/yellow] No VTT file found - falling back to text-based chunking"
                )
                input_for_processing = input_path

        else:
            supported_formats = [".txt", ".vtt", *audio_formats]
            console.print(f"[red]Error: Unsupported file format: {file_extension}[/red]")
            console.print(f"Supported formats: {', '.join(supported_formats)}")
            sys.exit(1)

        # Initialize components
        console.print("[blue]Initializing analysis components...[/blue]")
        chunker = TranscriptionChunker()

        # Chunk the transcription using the new file-based method
        with console.status("[bold green]Chunking transcription..."):
            blocks = chunker.chunk_from_file(str(input_for_processing))

        if not blocks:
            console.print("[red]Error: No analyzable blocks found in transcription.[/red]")
            sys.exit(1)

        # Display chunking results
        _display_chunking_results(blocks)

        if dry_run:
            console.print("[yellow]Dry run mode - stopping before API calls.[/yellow]")
            _display_analysis_plan(blocks)
            return

        # Analyze blocks
        analyzer = LectureAnalyzer()
        block_analyses = []

        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
        ) as progress:
            task = progress.add_task("Analyzing blocks...", total=len(blocks))

            for i, block in enumerate(blocks):
                progress.update(task, description=f"Analyzing block {i + 1}/{len(blocks)}")
                analysis = analyzer.analyze_block(block)
                block_analyses.append(analysis)
                progress.advance(task)

        console.print(f"[green]✓[/green] Completed analysis of {len(block_analyses)} blocks")

        # Aggregate results
        with console.status("[bold green]Aggregating results..."):
            aggregator = ScoreAggregator()
            complete_report = aggregator.create_complete_report(block_analyses)

        # Display results summary
        _display_results_summary(complete_report)

        # Format and save output
        formatter = MarkdownFormatter()

        # Determine output file paths
        if not output:
            timestamp = complete_report.timestamp.strftime("%Y%m%d_%H%M%S")
            if format == "both":
                output_md = f"analysis_{timestamp}.md"
                output_json = f"analysis_{timestamp}.json"
            elif format == "json":
                output = f"analysis_{timestamp}.json"
                output_md = None  # Not needed for JSON only
                output_json = output
            else:
                output = f"analysis_{timestamp}.md"
                output_md = output
                output_json = None  # Not needed for markdown only
        else:
            # User provided output path - use it directly based on format
            if format == "both":
                # For both formats, use provided path as base and add extensions
                base = output.rsplit(".", 1)[0] if "." in output else output
                output_md = f"{base}.md"
                output_json = f"{base}.json"
            elif format == "json":
                output_json = output
                output_md = None
            else:
                output_md = output
                output_json = None

        # Save markdown report
        if format in ["markdown", "both"]:
            markdown_path = output_md if output_md else output
            if markdown_path:
                markdown_content = formatter.format_complete_report(complete_report)

                with open(markdown_path, "w", encoding="utf-8") as f:
                    f.write(markdown_content)

                console.print(f"[green]✓[/green] Markdown report saved: {markdown_path}")

                # Save kurzfassung for Akademieleitung
                base_name = (
                    markdown_path.rsplit(".", 1)[0] if "." in markdown_path else markdown_path
                )
                kurzfassung_path = f"{base_name}_kurzfassung.md"
                kurzfassung_content = formatter.format_kurzfassung(complete_report)

                with open(kurzfassung_path, "w", encoding="utf-8") as f:
                    f.write(kurzfassung_content)

                console.print(f"[green]✓[/green] Kurzfassung saved: {kurzfassung_path}")

        # Save JSON report
        if format in ["json", "both"]:
            json_path = output_json if output_json else output
            if json_path:
                json_content = formatter.format_json_report(complete_report)

                with open(json_path, "w", encoding="utf-8") as f:
                    f.write(json_content)

                console.print(f"[green]✓[/green] JSON report saved: {json_path}")

        console.print("\n[bold green]Analysis completed successfully![/bold green]")
        console.print(f"Overall Score: [bold]{complete_report.overall_score}/5[/bold]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Analysis interrupted by user.[/yellow]")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        console.print(f"[red]Error: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


def _display_chunking_results(blocks: list[TimeBlock]) -> None:
    """Display the results of text chunking."""
    from .chunker import TranscriptionChunker

    chunker = TranscriptionChunker()

    table = Table(title="Chunking Results")
    table.add_column("Block", style="cyan")
    table.add_column("Time Range", style="magenta")
    table.add_column("Tokens", style="yellow", justify="right")
    table.add_column("Content Preview", style="green")

    for block in blocks:
        token_count = chunker.count_tokens(block.content)
        preview = (
            block.content[:100].replace("\n", " ") + "..."
            if len(block.content) > 100
            else block.content.replace("\n", " ")
        )

        # Color code token count based on limits
        token_color = "red" if token_count > 15000 else "yellow" if token_count > 10000 else "green"

        table.add_row(
            str(block.block_number),
            f"{block.start_time} - {block.end_time}",
            f"[{token_color}]{token_count}[/{token_color}]",
            preview,
        )

    console.print(table)


def _display_analysis_plan(blocks: list[TimeBlock]) -> None:
    """Display analysis plan for dry run mode."""
    console.print(
        Panel.fit(
            f"[bold]Analysis Plan[/bold]\n\n"
            f"• Total blocks to analyze: {len(blocks)}\n"
            f"• Each block will be scored on 10 criteria (1-5 scale)\n"
            f"• Structured JSON responses from OpenAI\n"
            f"• Aggregated final report with markdown tables\n"
            f"• Management summary and improvement suggestions",
            title="Dry Run Results",
        )
    )


def _display_results_summary(report: CompleteReport) -> None:
    """Display summary of analysis results."""
    # Overall score panel
    score_color = (
        "green" if report.overall_score >= 4 else "yellow" if report.overall_score >= 3 else "red"
    )
    console.print(
        Panel.fit(
            f"[bold {score_color}]{report.overall_score}/5[/bold {score_color}]",
            title="Overall Score",
        )
    )

    # Criteria summary table
    table = Table(title="Criteria Summary")
    table.add_column("Criterion", style="cyan")
    table.add_column("Score", justify="center")
    table.add_column("Status", justify="center")

    for criterion in report.aggregated_analysis.criteria_scores:
        score_style = (
            "green" if criterion.score >= 4 else "yellow" if criterion.score >= 3 else "red"
        )
        table.add_row(
            criterion.criterion_name_de,
            f"[{score_style}]{criterion.score}[/{score_style}]",
            criterion.traffic_light,
        )

    console.print(table)

    # Block summary
    console.print(f"\nAnalyzed {len(report.block_analyses)} time blocks")


if __name__ == "__main__":
    main()
